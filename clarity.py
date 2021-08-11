from alive_progress import alive_bar
from numpy import byte
from pathlib import Path
import click
import hashlib
import json
import os
import pymem
import pandas as pd
import re
import requests
import shutil
import sys
import zipfile

indexPattern = bytes.fromhex('49 4E 44 58 10 00 00 00')    # INDX block start
textPattern = bytes.fromhex('54 45 58 54 10 00 00')    # TEXT block start
endPattern = bytes.fromhex('46 4F 4F 54 10 00 00')    # FOOT block start
hex_dict = 'hex/hex_dict.csv'

def instantiate(exe):
    '''Instantiates a pymem instance that attaches to an executable.'''
    global handle
    global pm
    
    try:
        pm = pymem.Pymem(exe)
        handle = pm.process_handle
    except pymem.exception.ProcessNotFound:
        sys.exit(
            input(
                click.secho(
                    'Cannot find DQX. Ensure the game is launched and try'
                    'again.\nIf you launched DQX as admin, this program must'
                    'also run as admin.\n\nPress ENTER or close this window.',
                    fg='red'
                )
            )
        )

def address_scan(
    handle: int, pattern: bytes, multiple: bool, *, index_pattern_list = [],
    startAddress = 0, endAddress = 0x7FFFFFFF
    ):
    '''
    Scans the entire virtual memory space for a handle and returns addresses
    that match the given byte pattern.
    '''
    next_region = startAddress
    while next_region < endAddress:
        next_region, found = pymem.pattern.scan_pattern_page(
                                handle, next_region, pattern,
                                return_multiple = multiple)
        if found and multiple:
            index_pattern_list.append(found)
        elif found and not multiple:
            return found

def read_bytes(address, byte_count):
    '''Reads the given number of bytes starting at an address.'''
    return pm.read_bytes(address, byte_count)

def jump_to_address(handle: int, address: int, pattern: str):
    '''
    Jumps to the next matched address that matches a pattern. This function 
    exists as `scan_pattern_page` errors out when attempting to read protected
    pages, instead of just ignoring the page.
    '''
    mbi = pymem.memory.virtual_query(handle, address)
    page_bytes = pymem.memory.read_bytes(handle, address, mbi.RegionSize)
    match = re.search(pattern, page_bytes, re.DOTALL)
    
    if match:
        return address + match.span()[0]
    else:
        return None

def regenerate_hex(file):
    '''Parses a nested json file to convert strings to hex.'''
    en_hex_to_write = ''
    j = open(f'json/_lang/en/{file}.json', 'r', encoding='utf-8')
    data = json.loads(j.read())

    for item in data:
        key, value = list(data[item].items())[0]
        if re.search('^clarity_nt_char', key):
            en = '00'
        elif re.search('^clarity_ms_space', key):
            en = '00e38080'
        else:
            ja = '00' + key.encode('utf-8').hex()
            ja_raw = key
            ja_len = len(ja)

            if value:
                en = '00' + value.encode('utf-8').hex()
                en_raw = value
                en_len = len(en)
            else:
                en = ja
                en_len = ja_len
                
            if en_len > ja_len:
                print('\n')
                print(f'String too long. Please fix and try again.')
                print(f'File: {file}.json')
                print(f'JA string: {ja_raw} (byte length: {ja_len})')
                print(f'EN string: {en_raw} (byte length: {en_len})')
                print('\n')
                print('If you are not a translator, please post this message')
                print('in the #translation-discussion channel in Discord at')
                print('https://discord.gg/bVpNqVjEG5')
                print('\n')
                print('Press ENTER to exit the program.')
                print('(and ignore this loading bar - it is doing nothing.)')
                sys.exit(input())

            ja = ja.replace('7c', '0a')
            ja = ja.replace('5c74', '09')
            en = en.replace('7c', '0a')
            en = en.replace('5c74', '09')
            
            if ja_len != en_len:
                while True:
                    en += '00'
                    new_len = len(en)
                    
                    if (ja_len - new_len) == 0:
                        break
                    
        en_hex_to_write += en
    
    with open(f'hex/files/{file}.hex', 'w') as f:
        f.write(en_hex_to_write)
    
    checksum = __get_md5(f'json/_lang/en/{file}.json')
    with open(f'hex/checksums/{file}.md5', 'w') as f:
        f.write(checksum)

def get_latest_from_weblate():
    '''
    Downloads the latest zip file from the weblate branch and
    extracts the json files into the appropriate folder.
    '''
    filename = os.path.join(os.getcwd(), 'weblate.zip')
    url = 'https://github.com/jmctune/dqxclarity/archive/refs/heads/weblate.zip'

    try:
        r = requests.get(url)
        with open(filename, 'wb') as f:
            f.write(r.content)
    except requests.exceptions.RequestException as e:
        sys.exit(
            click.secho(
                'Failed to get latest files from weblate.\nMessage: {e}',
                fg='red'
            )
        )
        
    try:
        __delete_folder('json/_lang/en/dqxclarity-weblate')
        __delete_folder('json/_lang/en/en')
    except:
        pass
        
    archive = zipfile.ZipFile('weblate.zip')

    for file in archive.namelist():
        if file.startswith('dqxclarity-weblate/json/_lang/en'):
            archive.extract(file, 'json/_lang/en/')
            name = os.path.splitext(os.path.basename(file))
            shutil.move(
                f'json/_lang/en/{file}',
                f'json/_lang/en/{name[0]}{name[1]}'
            )
        if file.startswith('dqxclarity-weblate/json/_lang/ja'):
            archive.extract(file, 'json/_lang/ja/')
            name = os.path.splitext(os.path.basename(file))
            shutil.move(
                f'json/_lang/ja/{file}',
                f'json/_lang/ja/{name[0]}{name[1]}'
            )
        if file.startswith('dqxclarity-weblate/hex/hex_dict.csv'):
            archive.extract(file, 'hex/files/')
            name = os.path.splitext(os.path.basename(file))
            shutil.move(
                f'hex/files/{file}',
                f'hex/{name[0]}{name[1]}'
            )
    archive.close()
            
    __delete_folder('json/_lang/en/dqxclarity-weblate')
    __delete_folder('json/_lang/en/en')
    __delete_folder('json/_lang/ja/dqxclarity-weblate')
    __delete_folder('json/_lang/ja/ja')
    __delete_folder('hex/files/dqxclarity-weblate')
    os.remove('weblate.zip')
    click.secho('Now up to date!', fg='green')

def translate():
    '''Executes the translation process.'''
    instantiate('DQXGame.exe')

    index_pattern_list = []
    address_scan(
        handle, indexPattern, True, index_pattern_list = index_pattern_list
    )

    df = pd.read_csv(hex_dict, usecols = ['file', 'hex_string'], )

    with alive_bar(len(__flatten(index_pattern_list)), 
                                title='Translating..',
                                spinner='pulse',
                                bar='bubbles',
                                length=20) as bar:
        for address in __flatten(index_pattern_list):
            bar()
        
            hex_result = __split_string_into_spaces(
                            read_bytes(address, 64).hex().upper())
            csv_result = __flatten(
                            df[df.hex_string == hex_result].values.tolist())

            if csv_result != []:
                file = os.path.splitext(
                    os.path.basename(
                        csv_result[0]))[0].strip()

                json_md5 = __get_md5(f'json/_lang/en/{file}.json')

                try:
                    cached_md5 = Path(f'hex/checksums/{file}.md5').read_text()
                except:
                    open(f'hex/checksums/{file}.md5', 'a').close()
                    cached_md5 = Path(f'hex/checksums/{file}.md5').read_text()

                if json_md5 != cached_md5:
                    print(f'Regenerating {file}...')
                    regenerate_hex(file)

                start_addr = jump_to_address(handle, address, textPattern)
                if start_addr:
                    start_addr = start_addr + 14
                    result = type(byte)
                    while True:
                        start_addr = start_addr + 1
                        result = read_bytes(start_addr, 1)
                        
                        if result != b'\x00':
                            start_addr = start_addr - 1
                            break

                    data = bytes.fromhex(
                        Path(f'hex/files/{file}.hex').read_text())
                    pymem.memory.write_bytes(
                        handle, start_addr, data, len(data))

    click.secho(
        'Done. Continuing to scan for changes. Minimize this window '
        'and enjoy!', fg='green'
    )             

def reverse_translate():
    '''Translates the game back into Japanese.'''
    instantiate('DQXGame.exe')

    index_pattern_list = []
    address_scan(
        handle, indexPattern, True, index_pattern_list = index_pattern_list
    )

    df = pd.read_csv(
        hex_dict, usecols = ['file', 'hex_string']
    )

    with alive_bar(len(__flatten(index_pattern_list)), 
                                title='Untranslating..',
                                spinner='pulse',
                                bar='bubbles',
                                length=20) as bar:
        for address in __flatten(index_pattern_list):
            bar()
        
            hex_result = __split_string_into_spaces(
                read_bytes(address, 64).hex().upper())
            
            csv_result = __flatten(
                df[df.hex_string == hex_result].values.tolist())

            if csv_result != []:
                file = os.path.splitext(
                    os.path.basename(csv_result[0]))[0].strip()

                ja_hex_to_write = ''
                j = open(f'json/_lang/ja/{file}.json', 'r', encoding='utf-8')
                data = json.loads(j.read())

                for item in data:
                    key, value = list(data[item].items())[0]
                    if re.search('^clarity_nt_char', key):
                        ja = '00'
                    elif re.search('^clarity_ms_space', key):
                        ja = '00e38080'
                    else:
                        ja = '00' + key.encode('utf-8').hex()

                    ja = ja.replace('7c', '0a')
                    ja = ja.replace('5c74', '09')
                    ja_hex_to_write += ja

                start_addr = jump_to_address(handle, address, textPattern)
                if start_addr:

                    start_addr = start_addr + 14
                    result = type(byte)
                    while True:
                        start_addr = start_addr + 1
                        result = read_bytes(start_addr, 1)
                        
                        if result != b'\x00':
                            start_addr = start_addr - 1
                            break
                    
                    data = bytes.fromhex(ja_hex_to_write)
                    pymem.memory.write_bytes(
                        handle, start_addr, data, len(data))

def scan_for_ad_hoc_game_files():
    '''
    Continuously scans the DQXGame process for known addresses
    that are only loaded 'on demand'. Will pass the found
    address to translate().
    '''
    instantiate('DQXGame.exe')

    index_pattern_list = []
    address_scan(
        handle, indexPattern, True, index_pattern_list = index_pattern_list)

    df = pd.read_csv(
        hex_dict, usecols = ['file', 'hex_string'], )
    
    for address in __flatten(index_pattern_list):
        hex_result = __split_string_into_spaces(
            read_bytes(address, 64).hex().upper())
        csv_result = __flatten(
            df[df.hex_string == hex_result].values.tolist())
        
        if csv_result != []:
            file = os.path.splitext(os.path.basename(csv_result[0]))[0].strip()

            if 'adhoc' in file:
                json_md5 = __get_md5(f'json/_lang/en/{file}.json')

                try:
                    cached_md5 = Path(f'hex/checksums/{file}.md5').read_text()
                except:
                    open(f'hex/checksums/{file}.md5', 'a').close()
                    cached_md5 = Path(f'hex/checksums/{file}.md5').read_text()

                if json_md5 != cached_md5:
                    print(f'Regenerating {file}...')
                    regenerate_hex(file)

                start_addr = jump_to_address(handle, address, textPattern)
                if start_addr:
                    start_addr = start_addr + 14
                    result = type(byte)
                    
                    while True:
                        start_addr = start_addr + 1
                        result = read_bytes(start_addr, 1)
                        if result != b'\x00':
                            start_addr = start_addr - 1
                            break

                    data = bytes.fromhex(
                        Path(f'hex/files/{file}.hex').read_text())
                    pymem.memory.write_bytes(
                        handle, start_addr, data, len(data))

def dump_all_game_files():
    '''
    Searches for all INDEX entries in memory and dumps
    the entire region, then converts said region to nested json.
    '''
    instantiate('DQXGame.exe')
    __delete_folder('game_file_dumps')
    
    directories = [
        'game_file_dumps/known/en',
        'game_file_dumps/known/ja',
        'game_file_dumps/unknown/en',
        'game_file_dumps/unknown/ja'
    ]
    
    unknown_file = 1
    
    for dir in directories:
        Path(dir).mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(
        hex_dict, usecols = ['file', 'hex_string'])

    index_pattern_list = []
    address_scan(
        handle, indexPattern, True, index_pattern_list = index_pattern_list)

    with alive_bar(len(__flatten(index_pattern_list)), 
                                title='Dumping..',
                                spinner='pulse',
                                bar='bubbles',
                                length=20) as bar:

        for address in __flatten(index_pattern_list):
            bar()
        
            hex_result = __split_string_into_spaces(
                            read_bytes(
                                address, 64).hex().upper()
                        )
            start_addr = jump_to_address(handle, address, textPattern) 
            if start_addr is not None: 
                end_addr = jump_to_address(handle, start_addr, endPattern)
                if end_addr is not None:
                    bytes_to_read = end_addr - start_addr
                    
                    game_data = read_bytes(
                        start_addr, bytes_to_read).hex()[24:].strip('00')
                    if len(game_data) % 2 != 0:
                        game_data = game_data + '0'
                        
                    game_data = bytes.fromhex(game_data).decode('utf-8')
                    game_data = game_data.replace('\x0a', '\x7c')
                    game_data = game_data.replace('\x00', '\x0a')
                    game_data = game_data.replace('\x09', '\x5c\x74')
                    
                    jsondata_ja = {}
                    jsondata_en = {}
                    number = 1
                    
                    for line in game_data.split('\n'):
                        json_data_ja = __format_to_json(
                                        jsondata_ja, line, 'ja', number)
                        json_data_en = __format_to_json(
                                        jsondata_en, line, 'en', number)
                        number += 1

                    json_data_ja = json.dumps(
                        jsondata_ja,
                        indent=4,
                        sort_keys=False,
                        ensure_ascii=False
                    )
                    json_data_en = json.dumps(
                        jsondata_en,
                        indent=4,
                        sort_keys=False,
                        ensure_ascii=False
                    )
                    
                    # Determine whether to write to consider file or not
                    csv_result = __flatten(
                        df[df.hex_string == hex_result].values.tolist())
                    if csv_result != []:
                        file = os.path.splitext(
                            os.path.basename(
                                csv_result[0]))[0].strip() + '.json'
                        json_path_ja = 'game_file_dumps/known/ja'
                        json_path_en = 'game_file_dumps/known/en'
                    else:
                        file = str(unknown_file) + '.json'
                        unknown_file += 1
                        json_path_ja = 'game_file_dumps/unknown/ja'
                        json_path_en = 'game_file_dumps/unknown/en'
                        print(f'Unknown file found: {file}')
                        __write_file(
                            'game_file_dumps',
                            'consider_master_dict.csv',
                            'a',
                            f'json\\_lang\\en\\{file},{hex_result}\n'
                        )
                    
                    __write_file(json_path_ja, file, 'w+', json_data_ja)
                    __write_file(json_path_en, file, 'w+', json_data_en)

def migrate_translated_json_data():
    '''
    Runs _HyDE_'s json migration tool to move a populated nested
    json file to a file that was made with dump_all_game_files().
    '''
    old_directories = [
        'json/_lang/en'
    ]
    
    new_directories = [
        'game_file_dumps/known/en'
    ]
    
    # Don't reorganize these
    destination_directories = [
        'hyde_json_merge/src',
        'hyde_json_merge/dst',
        'hyde_json_merge/out'
    ]
    
    for d in destination_directories:
        for f in os.listdir(d):
            os.remove(os.path.join(d, f))
            
    for d in old_directories:
        src_files = os.listdir(d)
        for f in src_files:
            full_file_name = os.path.join(d, f)
            if os.path.isfile(full_file_name):
                shutil.copy(full_file_name, destination_directories[0])
                
    for d in new_directories:
        src_files = os.listdir(d)
        for f in src_files:
            full_file_name = os.path.join(d, f)
            if os.path.isfile(full_file_name):
                shutil.copy(full_file_name, destination_directories[1])
                    
    for f in os.listdir('hyde_json_merge/src'):
        os.system(f'hyde_json_merge\json-conv.exe -s hyde_json_merge/src/{f} -d hyde_json_merge/dst/{f} -o hyde_json_merge/out/{f}')

def __write_file(path, file, type, data):
    '''Writes a string to a file.'''
    file = open(f'{path}/{file}', type, encoding='utf-8')
    file.write(data)
    file.close()

def __format_to_json(json_data, data, lang, number):
    '''Accepts data that is used to return a nested json.'''
    json_data[number]={}
    if data == '':
        json_data[number][f'clarity_nt_char_{number}']=f'clarity_nt_char_{number}'
    elif data == '　':
        json_data[number][f'clarity_ms_space_{number}']=f'clarity_ms_space_{number}'
    else:
        if lang == 'ja':
            json_data[number][data]=data
        else:
            json_data[number][data]=''
        
    return json_data

def __get_md5(file):
    '''Returns the MD5 hash of a file's contents.'''
    return hashlib.md5(open(file,'rb').read()).hexdigest()

def __flatten(list):
    '''Takes a list of lists and flattens it into one list.'''
    return [item for sublist in list for item in sublist]

def __split_string_into_spaces(string):
    '''
    Breaks a string up by putting spaces between every two characters.
    Used to format a hex string.
    '''
    return " ".join(string[i:i+2] for i in range(0, len(string), 2))

def __delete_folder(folder):
    '''Deletes a folder and all subfolders.'''
    try:
        shutil.rmtree(folder)
    except:
        pass