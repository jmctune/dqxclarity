import textwrap
import requests
import json
import sys
import ctypes
import datetime
import configparser
from os.path import exists
from langdetect import detect
import re
import sqlite3


def deepl_translate(dialog_text, is_pro, api_key, region_code):
    '''Uses DeepL Translate to translate text to the specified language.'''
    if is_pro == 'True':
        api_url = 'https://api.deepl.com/v2/translate'
    else:
        api_url = 'https://api-free.deepl.com/v2/translate'

    payload = {'auth_key': api_key, 'text': dialog_text, 'target_lang': region_code}
    r = requests.post(api_url, data=payload, timeout=5)
    translated_text = r.content

    return json.loads(translated_text)['translations'][0]['text']

def google_translate(dialog_text, api_key, region_code):
    '''Uses Google Translate to translate text to the specified language.'''
    uri = '&source=ja&target=' + region_code + '&q=' + dialog_text + '&format=text'
    api_url = 'https://www.googleapis.com/language/translate/v2?key=' + api_key + uri
    headers = {'Content-Type': 'application/json'}

    r = requests.post(api_url, headers=headers, timeout=5)
    translated_text = r.content
    
    return json.loads(translated_text)['data']['translations'][0]['translatedText']

def translate(translation_service, is_pro, dialog_text, api_key, region_code):
    if translation_service == 'deepl':
        return deepl_translate(dialog_text, is_pro, api_key, region_code)
    elif translation_service == 'google':
        return google_translate(dialog_text, api_key, region_code)

def sanitized_dialog_translate(translation_service, is_pro, dialog_text, api_key, region_code) -> str:
    '''
    Does a bunch of text sanitization to handle tags seen in DQX, as well as automatically
    splitting the text up into chunks to be fed into the in-game dialog window.
    '''
    if detect(dialog_text) == 'ja':
        output = re.sub('<br>', ' ', dialog_text)
        output = re.split(r'(<.+?>)', output)
        final_string = ''
        for item in output:
            if item == '':
                continue
            if item == '<br>':  # we'll manage our own line breaks later
                final_string += ' '
                continue
            alignment = ['<center>', '<right>']  # center and right aligned text doesn't work well in this game with ascii
            if item in alignment:
                final_string += ''
                continue
            if re.findall('<(.*?)>', item, re.DOTALL) or item == '\n':
                final_string += item
            else:
                # lists don't have puncuation. remove new lines before sending to translate
                puncs = ['。', '？', '！']
                if any(x in item for x in puncs):
                    sanitized = re.sub('\n', ' ', item) + '\n'
                    sanitized = re.sub('\u3000', ' ', sanitized)  # replace full width spaces with ascii spaces
                    sanitized = re.sub('「', '', sanitized)  # these create a single double quote, which look weird in english
                    sanitized = re.sub('…', '', sanitized)  # elipsis doesn't look natural
                    sanitized = re.sub('', '', sanitized)  # romaji player names use this. remove as it messes up the translation
                    translation = translate(translation_service, is_pro, sanitized, api_key, region_code)
                    translation = translation.strip()
                    translation = re.sub('   ', ' ', translation)  # translation sometimes comes back with a strange number of spaces
                    translation = re.sub('  ', ' ', translation)
                    translation = textwrap.fill(translation, width=45, replace_whitespace=False)

                    # figure out where to put <br> to break up text 
                    count = 1
                    count_list = [3, 6, 9, 12, 15, 18, 21, 24, 27, 30]
                    for line in translation.split('\n'):
                        final_string += line
                        if count in count_list:
                            final_string += '\n<br>\n'
                        else:
                            final_string += '\n'
                        count += 1

                else:
                    sanitized = item
                    sanitized = re.sub('\u3000', ' ', sanitized)  # replace full width spaces with ascii spaces
                    sanitized = re.sub('「', '', sanitized)  # these create a single double quote, which look weird in english
                    sanitized = re.sub('…', '', sanitized)  # elipsis doesn't look natural with english
                    translation = translate(translation_service, is_pro, sanitized, api_key, region_code)
                    final_string += translation

                def rreplace(s, old, new, occurrence):
                    li = s.rsplit(old, occurrence)
                    return new.join(li)

                # this cleans up any blank newlines
                final_string = "\n".join([ll.rstrip() for ll in final_string.splitlines() if ll.strip()])        

                # the above code adds a line break every 3 lines, but doesn't account for the last section
                # of dialog that doesn't need a <br> if it's just one window of dialog, so remove it
                final_string_count = final_string.count('\n')
                count = 0
                for line in final_string.split('\n'):
                    if count == final_string_count:
                        if '<br>' in line:
                            final_string = rreplace(final_string, '<br>', '', 1)
                            final_string = '\n'.join([ll.rstrip() for ll in final_string.splitlines() if ll.strip()])
                    count += 1
                
        return final_string
    else:
        return dialog_text

def write_to_log(is_enabled, source_text, translated_text, language):
    '''Logs text to a file.'''
    if is_enabled == 'True':
        data = logger_timestamp() + '\n' + 'ja: ' + source_text + '\n' + language + ': ' + translated_text  + '\n\n'
        with open('dqx_text_log.txt', 'a', encoding='utf-8') as open_file:
            open_file.write(data)

def sqlite_read(text_to_query, language):
    '''Reads text from the database.'''
    escaped_text = text_to_query.replace("'","''")

    try:
        conn = sqlite3.connect('clarity_dialog.db')
        cursor = conn.cursor()
        selectQuery = f'SELECT {language} FROM dialog WHERE ja = \'{escaped_text}\''
        cursor.execute(selectQuery)
        results = cursor.fetchone()
        
        if results is not None:
            return results[0].replace("''", "'")
        else:
            return None
        
    except sqlite3.Error as error:
        print(f'[DEBUG] Failed to query SQLite: {error}')
    finally:
        if conn:
            conn.close()

def sqlite_write_dynamic(source_text, npc_name, translated_text, language):
    '''Writes or updates text to the database.'''
    escaped_text = translated_text.replace("'","''")

    try:
        conn = sqlite3.connect("clarity_dialog.db")
        selectQuery = f'SELECT ja FROM dialog WHERE ja = \'{source_text}\''
        insertQuery = f'INSERT INTO dialog (ja, npc_name, {language}) VALUES (\'{source_text}\', \'{npc_name}\', \'{escaped_text}\')'
        updateQuery = f'UPDATE dialog SET {language} = \'{escaped_text}\' WHERE ja = \'{source_text}\''

        cursor = conn.cursor()
        results = cursor.execute(selectQuery)

        if results.fetchone() is None:
            cursor.execute(insertQuery)
        else:
            cursor.execute(updateQuery)

        conn.commit()
        cursor.close()
    except sqlite3.Error as error:
        print(f'[DEBUG] Failed to add data to SQLite: {error}')
    finally:
        if conn:
            conn.close()

def check_deepl_remaining_char_count(key, is_pro):
    if is_pro == 'True':
        url = "https://api.deepl.com/v2"
    else:
        url = "https://api-free.deepl.com/v2"
    url += "/usage?auth_key=" + key
    response = requests.get(url)
    if response.status_code != 200:
        return False
    else:
        return True

def test_google_translate_api_key(key):
    body = "&source=ja" + "&target=" + 'en' + "&q="
    url = "https://www.googleapis.com/language/translate/v2?key=" + key + body
    response = requests.get(url)
    if response.status_code == 200:
        return True
    else:
        return False

def sanitize_text_before_translate(text: str) -> str:
    sanitized_text = re.sub('<br>', '', text)
    sanitized_text = re.sub('「', '', sanitized_text)
    sanitized_text = re.sub('…', '', sanitized_text)

    return sanitized_text

def sanitized_text_after_translate(text: str) -> str:
    if '　' in text:
        return text.replace('　', ' ')
    else:
        return text

def determine_translation_service():
    '''Parses the user config file to get information needed to make translation calls.'''
    filename = 'user_settings.ini'
    config = configparser.ConfigParser()
    if not exists(filename):
        config['translation'] = {'EnableDeepLTranslate': 'False',
                                'EnableDeepLProAPIs': 'False',
                                'DeepLTranslateKey': 'null',
                                'EnableGoogleTranslate': 'False',
                                'GoogleTranslateKey': 'null',
                                'RegionCode': 'EN'
                                }
        config['behavior'] = {}
        config['behavior']['EnableDialogLogging'] = 'False'
        with open(filename, 'w') as configfile:
            config.write(configfile)

    config.read(filename)
    if 'translation' in config:
        if 'EnableDeepLTranslate' in config['translation']:
            deepl_translate_choice = config['translation']['EnableDeepLTranslate']
        if 'EnableDeepLProAPIs' in config['translation']:
            deepl_pro = config['translation']['EnableDeepLProAPIs']
        if 'DeepLTranslateKey' in config['translation']:
            deepl_translate_key = config['translation']['DeepLTranslateKey']
        if 'EnableGoogleTranslate' in config['translation']:
            google_translate_choice = config['translation']['EnableGoogleTranslate']
        if 'GoogleTranslateKey' in config['translation']:
            google_translate_key = config['translation']['GoogleTranslateKey']
        if 'RegionCode' in config['translation']:
            region_code = config['translation']['RegionCode']
    if 'behavior' in config:
        if 'EnableDialogLogging' in config['behavior']:
            enable_dialog_logging = config['behavior']['EnableDialogLogging']

    if (deepl_translate_choice == 'False' and google_translate_choice == 'False'):
        ctypes.windll.user32.MessageBoxW(0, f"You need to enable a translation service in user_settings.ini. Open the file in Notepad and set it up.\n\nCurrent values:\n\nEnableDeepLTranslate: {config['translation']['EnableDeepLTranslate']}\nEnableGoogleTranslate: {config['translation']['EnableGoogleTranslate']}", "[dqxclarity] No translation service enabled", 0x10)
        sys.exit()

    if (deepl_translate_choice == 'True' and google_translate_choice == 'True'):
        ctypes.windll.user32.MessageBoxW(0, f"Only enable one translation service in user_settings.ini. Open the file in Notepad and set it up.\n\nCurrent values:\n\nEnableDeepLTranslate: {config['translation']['EnableDeepLTranslate']}\nEnableGoogleTranslate: {config['translation']['EnableGoogleTranslate']}", "[dqxclarity] Too many translation serviced enabled", 0x10)
        sys.exit()
        
    if (deepl_translate_choice != 'True' and deepl_translate_choice != 'False'):
        ctypes.windll.user32.MessageBoxW(0, f"Invalid value detected for EnableDeepLTranslate. Open user_settings.ini in Notepad and fix it.\n\nValid values are: True, False\n\nCurrent values:\n\nEnableDeepLTranslate: {config['translation']['EnableDeepLTranslate']}", "[dqxclarity] Misconfigured boolean", 0x10)
        sys.exit()
        
    if (google_translate_choice != 'True' and google_translate_choice != 'False'):
        ctypes.windll.user32.MessageBoxW(0, f"Invalid value detected for EnableGoogleTranslate. Open user_settings.ini in Notepad and fix it.\n\nValid values are: True, False\n\nCurrent values:\n\nEnableGoogleTranslate: {config['translation']['EnableGoogleTranslate']}", "[dqxclarity] Misconfigured boolean", 0x10)
        sys.exit()
        
    if (deepl_translate_key == 'null' and google_translate_key == 'null'):
        ctypes.windll.user32.MessageBoxW(0, f"You need to configure an API key in user_settings.ini. Open the file in Notepad and set it up.\n\nCurrent values:\n\nDeepLTranslateKey: {config['translation']['DeepLTranslateKey']}\nGoogleTranslateKey: {config['translation']['GoogleTranslateKey']}", "[dqxclarity] No API key configured", 0x10)
        sys.exit()
        
    if (deepl_pro != 'True' and deepl_pro != 'False'):
        ctypes.windll.user32.MessageBoxW(0, f"Invalid value detected for EnableDeepLProAPIs. Open user_settings.ini in Notepad and fix it.\n\nValid values are: True, False\n\nCurrent values:\n\nEnableDeepLProAPIs: {config['translation']['EnableDeepLProAPIs']}", "[dqxclarity] Misconfigured boolean", 0x10)
        sys.exit()
        
    if (enable_dialog_logging != 'True' and enable_dialog_logging != 'False'):
        ctypes.windll.user32.MessageBoxW(0, f"Invalid value detected for EnableDialogLogging. Open user_settings.ini in Notepad and fix it.\n\nValid values are: True, False\n\nCurrent values:\n\nEnableDialogLogging: {config['translation']['EnableDialogLogging']}", "[dqxclarity] Misconfigured boolean", 0x10)
        sys.exit()

    if deepl_translate_choice == 'True':
        if not check_deepl_remaining_char_count(deepl_translate_key, deepl_pro):
            ctypes.windll.user32.MessageBoxW(0, f"Your DeepL API key did not validate successfully. Check the key and region code then try again.\n\nCurrent values:\n\nRegionCode: {config['translation']['RegionCode']}\nDeepLTranslateKey: {config['translation']['DeepLTranslateKey']}", "[dqxclarity] API key failed to validate", 0x10)
            sys.exit()
            
    if google_translate_choice == 'True':
        if not test_google_translate_api_key(google_translate_key):
            ctypes.windll.user32.MessageBoxW(0, f"Your Google Translate API key did not validate successfully. Check the key and region code then try again.\n\nCurrent values:\n\nRegionCode: {config['translation']['RegionCode']}\nGoogleTranslateKey: {config['translation']['GoogleTranslateKey']}", "[dqxclarity] API key failed to validate", 0x10)
            sys.exit()

    dic = dict()
    if deepl_translate_choice == 'True':
        dic['TranslateService'] = 'deepl'
        dic['TranslateKey'] = deepl_translate_key
        dic['IsPro'] = deepl_pro
    elif google_translate_choice == 'True':
        dic['TranslateService'] = 'google'
        dic['TranslateKey'] = google_translate_key
        dic['IsPro'] = 'False'
        
    dic['EnableDialogLogging'] = enable_dialog_logging
    dic['RegionCode'] = region_code

    return dic
