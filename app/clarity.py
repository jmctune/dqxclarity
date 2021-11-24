# -*- coding: utf-8 -*-
'''
Functions used by main.py to perform various actions that manipulate memory.
'''

from pathlib import Path
import csv
import json
import os
import re
import shutil
import sys
import zipfile
import random
from alive_progress import alive_bar
import pykakasi
from loguru import logger
import requests
from errors import messageBoxFatalError
from memory import (
    read_bytes,
    read_string,
    write_bytes,
    pattern_scan,
    get_start_of_game_text,
    find_first_match
)
from signatures import (
    index_pattern,
    foot_pattern,
    npc_monster_byte_pattern,
    player_name_byte_pattern
)

HEX_DICT = 'hex_dict.csv'


def generate_hex(file):
    '''Parses a nested json file to convert strings to hex.'''
    en_hex_to_write = ''
    data = __read_json_file(file, 'en')
    for item in data:
        key, value = list(data[item].items())[0]
        if re.search('^clarity_nt_char', key):
            en = '00'
        elif re.search('^clarity_ms_space', key):
            en = '00e38080'
        else:
            ja = key.encode('utf-8').hex() + '00'
            ja_raw = key
            ja_len = len(ja)
            if value:
                en = value.encode('utf-8').hex() + '00'
                en_raw = value
                en_len = len(en)
            else:
                en = ja
                en_len = ja_len
            if en_len > ja_len:
                logger.error('\n')
                logger.error('String too long. Please fix and try again.')
                logger.error(f'File: {file}.json')
                logger.error(f'JA string: {ja_raw} (byte length: {ja_len})')
                logger.error(f'EN string: {en_raw} (byte length: {en_len})')

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


    return en_hex_to_write

def get_latest_from_weblate():
    '''
    Downloads the latest zip file from the weblate branch and
    extracts the json files into the appropriate folder.
    '''
    filename = os.path.join(os.getcwd(), 'weblate.zip')
    url = 'https://github.com/jmctune/dqxclarity/archive/refs/heads/weblate.zip'

    try:
        github_request = requests.get(url)
        with open(filename, 'wb') as zip_file:
            zip_file.write(github_request.content)
    except requests.exceptions.RequestException as e:
        messageBoxFatalError('Failed to update!',
                            f'Failed to get latest files from weblate.\nMessage: {e}')
    __delete_folder('json/_lang/en/dqxclarity-weblate')
    __delete_folder('json/_lang/en/en')

    with zipfile.ZipFile('weblate.zip') as archive:
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
            if file.startswith(f'dqxclarity-weblate/{HEX_DICT}'):
                archive.extract(file, '.')
                name = os.path.splitext(os.path.basename(file))
                shutil.move(
                    f'{file}',
                    f'{name[0]}{name[1]}'
                )

    __delete_folder('json/_lang/en/dqxclarity-weblate')
    __delete_folder('json/_lang/en/en')
    __delete_folder('json/_lang/ja/dqxclarity-weblate')
    __delete_folder('json/_lang/ja/ja')
    __delete_folder('hex/files/dqxclarity-weblate')
    __delete_folder('dqxclarity-weblate')
    os.remove('weblate.zip')
    logger.info('Now up to date!')

def translate():
    '''Executes the translation process.'''
    index_list = pattern_scan(pattern=index_pattern, return_multiple=True)
    list_length = len(index_list)

    with alive_bar(list_length, title='Translating..', theme='musical', length=20) as bar:
        for index_address in index_list:
            bar()
            hex_result = split_hex_into_spaces(str(read_bytes(index_address, 64).hex()))
            csv_result = query_csv(hex_result)
            if csv_result:
                file = csv_result['file']
                hex_to_write = bytes.fromhex(generate_hex(file))
                text_address = get_start_of_game_text(index_address)
                if text_address:
                    try:
                        # this just tests that we can decode what we should be writing
                        game_hex = read_bytes(text_address, len(hex_to_write)).hex()
                        decoded_bytes = bytes.fromhex(game_hex).decode('utf-8')
                    except:
                        continue

                    write_bytes(text_address, hex_to_write)

def write_adhoc_entry(start_addr: int, hex_str: str) -> dict:
    '''
    Checks the stored json files for a matching adhoc file. If found,
    converts the json into bytes and writes bytes at the appropriate
    address.
    '''
    results = dict()
    hex_result = split_hex_into_spaces(hex_str)
    csv_result = query_csv(hex_result)
    if csv_result:
        file = csv_result['file']
        if 'adhoc' in file:
            hex_to_write = bytes.fromhex(generate_hex(file))
            index_address = find_first_match(start_addr, index_pattern)
            if index_address:
                text_address = get_start_of_game_text(index_address)
                if text_address:
                    write_bytes(text_address, hex_to_write)
                    results['success'] = True
                    results['file'] = file
                    return results
    else:
        results['success'] = False
        filename = str(random.randint(1, 1000000000))
        Path('new_adhoc_dumps/en').mkdir(parents=True, exist_ok=True)
        Path('new_adhoc_dumps/ja').mkdir(parents=True, exist_ok=True)

        new_csv = Path('new_adhoc_dumps/new_hex_dict.csv')
        if new_csv.is_file():
            csv_result = query_csv(hex_result)
            if csv_result:  # if we have an entry, don't make another one
                results['file'] = None
                return results
        else:
            __write_file('new_adhoc_dumps', 'new_hex_dict.csv', 'a', 'file,hex_string\n')

        # get number of bytes to read from start
        begin_address = get_start_of_game_text(start_addr)  # make sure we start on the first byte of the first letter
        end_address = find_first_match(begin_address, foot_pattern)
        bytes_to_read = end_address - begin_address

        # dump game file
        game_file = dump_game_file(begin_address, bytes_to_read)
        ja_data = game_file['ja']
        en_data = game_file['en']
        __write_file('new_adhoc_dumps', 'new_hex_dict.csv', 'a', f'{filename},{hex_result}\n')
        __write_file('new_adhoc_dumps/ja', f'{filename}.json', 'w', ja_data)
        __write_file('new_adhoc_dumps/en', f'{filename}.json', 'w', en_data)
        results['file'] = filename
        return results

def scan_for_npc_names():
    '''
    Continuously scans the DQXGame process for known addresses
    that are related to a specific pattern to translate names.
    '''
    npc_data = __read_json_file('json/_lang/en/npc_names.json', 'en')
    monster_data = __read_json_file('json/_lang/en/monsters.json', 'en')

    logger.info('Starting NPC/monster name scanning.')

    while True:
        index_list = pattern_scan(pattern=npc_monster_byte_pattern, return_multiple=True)

        if index_list == []:
            continue

        for address in index_list:
            if read_bytes(address, 2) == b'\x8C\x75':  # monsters
                data = monster_data
                name_addr = address + 12  # jump to name
                end_addr = address + 12
            elif read_bytes(address, 2) == b'\x90\x87':  # npcs
                data = npc_data
                name_addr = address + 12  # jump to name
                end_addr = address + 12
            else:
                continue

            name_hex = bytearray()
            result = ''
            while result != b'\x00':
                result = read_bytes(end_addr, 1)
                end_addr = end_addr + 1
                if result == b'\x00':
                    end_addr = end_addr - 1   # Remove the last 00

                name_hex += result

            name_hex = name_hex.rstrip(b'\x00')
            try:
                name = name_hex.decode('utf-8')
            except UnicodeDecodeError:
                continue
            for item in data:
                key, value = list(data[item].items())[0]
                if re.search(f'^{name}+$', key):
                    if value:
                        write_bytes(name_addr, str.encode(value) + b'\x00')

def scan_for_player_names():
    '''
    Continuously scans the DQXGame process for known addresses
    that are related to a specific pattern to translate player names.
    '''
    kks = pykakasi.kakasi()

    logger.info('Starting player name scanning.')

    while True:
        player_list = pattern_scan(pattern=player_name_byte_pattern, return_multiple=True)
        if player_list == []:
            continue

        for address in player_list:
            player_name_address = address + 17
            try:
                ja_player_name = read_string(player_name_address)
            except UnicodeDecodeError:
                continue

            romaji_name = kks.convert(ja_player_name)[0]['hepburn'].capitalize()
            write_bytes(player_name_address, b'\x04' + romaji_name.encode('utf-8') + b'\x00')

def dump_game_file(start_addr: int, num_bytes_to_read: int):
    '''
    Dumps a game file given its start and end address. Formats into a json
    friendly file to be used by clarity for both ja and en.

    start_addr: Where to start our read operation to dump (should start at TEXT)
    num_bytes_to_read: How many bytes should we should dump from the start_addr
    '''
    game_data = read_bytes(start_addr, num_bytes_to_read).hex().strip('00')
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
        json_data_ja = __format_to_json(jsondata_ja, line, 'ja', number)
        json_data_en = __format_to_json(jsondata_en, line, 'en', number)
        number += 1

    json_data_ja = json.dumps(
        jsondata_ja,
        indent=2,
        sort_keys=False,
        ensure_ascii=False
    )
    json_data_en = json.dumps(
        jsondata_en,
        indent=2,
        sort_keys=False,
        ensure_ascii=False
    )

    dic = dict()
    dic['ja'] = json_data_ja
    dic['en'] = json_data_en

    return dic

def dump_all_game_files():
    '''
    Searches for all INDX entries in memory and dumps
    the entire region, then converts said region to nested json.
    '''
    __delete_folder('game_file_dumps')

    directories = [
        'game_file_dumps/known/en',
        'game_file_dumps/known/ja',
        'game_file_dumps/unknown/en',
        'game_file_dumps/unknown/ja'
    ]

    unknown_file = 1

    for folder in directories:
        Path(folder).mkdir(parents=True, exist_ok=True)

    game_file_addresses = pattern_scan(pattern=index_pattern, return_multiple=True)

    hex_blacklist = [
        # license file
        '49 4E 44 58 10 00 00 00 10 00 00 00 00 00 00 00 73 4C 01 00 00 00 00 00 89 50 01 00 D8 BB 00 00 46 4F 4F 54 10 00 00 00 00 00 00 00 00 00 00 00 54 45 58 54 10 00 00 00 00 BC 00 00 00 00 00 00'
    ]

    with alive_bar(len(game_file_addresses),
                                title='Dumping..',
                                theme='smooth',
                                length=20) as bar:
        for address in game_file_addresses:
            bar()
            hex_result = split_hex_into_spaces(str(read_bytes(address, 64).hex()))
            if hex_result in hex_blacklist:
                continue
            start_addr = get_start_of_game_text(address)  # make sure we start on the first byte of the first letter
            if start_addr is not None:
                end_addr = find_first_match(start_addr, foot_pattern)
                if end_addr is not None:
                    bytes_to_read = end_addr - start_addr
                    if bytes_to_read < 0:
                        continue
                    game_data = read_bytes(start_addr, bytes_to_read).rstrip(b'\x00').hex()
                    if len(game_data) % 2 != 0:
                        game_data = game_data + '0'

                    try:
                        game_data = bytes.fromhex(game_data).decode('utf-8')
                    except UnicodeDecodeError:
                        continue  # incomplete files are sometimes loaded. ignore them
                    game_data = game_data.replace('\x0a', '\x7c')
                    game_data = game_data.replace('\x00', '\x0a')
                    game_data = game_data.replace('\x09', '\x5c\x74')

                    jsondata_ja = {}
                    jsondata_en = {}
                    number = 1

                    for line in game_data.split('\n'):
                        json_data_ja = __format_to_json(jsondata_ja, line, 'ja', number)
                        json_data_en = __format_to_json(jsondata_en, line, 'en', number)
                        number += 1

                    json_data_ja = json.dumps(
                        jsondata_ja,
                        indent=2,
                        sort_keys=False,
                        ensure_ascii=False
                    )
                    json_data_en = json.dumps(
                        jsondata_en,
                        indent=2,
                        sort_keys=False,
                        ensure_ascii=False
                    )

                    # Determine whether to write to consider file or not
                    csv_result = query_csv(hex_result)
                    if csv_result:
                        file = os.path.splitext(
                            os.path.basename(
                                csv_result['file']))[0].strip() + '.json'
                        json_path_ja = 'game_file_dumps/known/ja'
                        json_path_en = 'game_file_dumps/known/en'
                    else:
                        file = str(unknown_file) + '.json'
                        unknown_file += 1
                        json_path_ja = 'game_file_dumps/unknown/ja'
                        json_path_en = 'game_file_dumps/unknown/en'
                        logger.info(f'Unknown file found: {file}')
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
        '../hyde_json_merge/src',
        '../hyde_json_merge/dst',
        '../hyde_json_merge/out'
    ]

    for folder in destination_directories:
        for filename in os.listdir(folder):
            os.remove(os.path.join(folder, filename))

    for folder in old_directories:
        src_files = os.listdir(folder)
        for filename in src_files:
            full_file_name = os.path.join(folder, filename)
            if os.path.isfile(full_file_name):
                shutil.copy(full_file_name, destination_directories[0])

    for folder in new_directories:
        src_files = os.listdir(folder)
        for filename in src_files:
            full_file_name = os.path.join(folder, filename)
            if os.path.isfile(full_file_name):
                shutil.copy(full_file_name, destination_directories[1])

    for filename in os.listdir('../hyde_json_merge/src'):
        os.system(f'../hyde_json_merge\json-conv.exe -s ../hyde_json_merge/src/{filename} -d ../hyde_json_merge/dst/{filename} -o ../hyde_json_merge/out/{filename}')  # pylint: disable=anomalous-backslash-in-string,line-too-long

def check_for_updates():
    '''
    Checks github for updates.
    '''
    url = 'https://raw.githubusercontent.com/jmctune/dqxclarity/main/sha'

    exe_sha = False
    if exe_sha is False:
        return

    try:
        github_request = requests.get(url)
    except requests.exceptions.RequestException as e:
        logger.warning(f'Failed to check latest version. Running anyways.\nMessage: {e}')
        return

    if github_request.text != exe_sha:
        logger.info('An update is available at https://github.com/jmctune/dqxclarity/releases', fg='green')
    else:
        logger.info('Up to date!')
  
    return

def query_csv(hex_pattern) -> dict:
    with open('hex_dict.csv') as file:
        reader = csv.DictReader(file)
        return_dict = dict()
        for row in reader:
            if row['hex_string'] == hex_pattern:
                return_dict['file'] = row['file']
                return_dict['hex_string'] = row['hex_string']
                return return_dict

def __read_json_file(file, region_code):
    with open(file, 'r', encoding='utf-8') as json_data:
        return json.loads(json_data.read())

def __write_file(path, filename, attr, data):
    '''Writes a string to a file.'''
    with open(f'{path}/{filename}', attr, encoding='utf-8') as open_file:
        open_file.write(data)

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

def __flatten(list_of_lists):
    '''Takes a list of lists and flattens it into one list.'''
    return [item for sublist in list_of_lists for item in sublist]

def split_hex_into_spaces(hex_str: str):
    '''
    Breaks a string up by putting spaces between every two characters.
    Used to format a hex string.
    '''
    spaced_str = " ".join(hex_str[i:i+2] for i in range(0, len(hex_str), 2))
    return spaced_str.upper()

def __delete_folder(folder):
    '''Deletes a folder and all subfolders.'''
    shutil.rmtree(folder, ignore_errors=True)

def __parse_filename_from_csv_result(csv_result):
    '''Parse the filename from the supplied csv result.'''
    return os.path.splitext(os.path.basename(csv_result[0]))[0].strip()
