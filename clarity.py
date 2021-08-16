'''
Functions used by main.py to perform various actions that manipulate memory.
'''

from pathlib import Path
import json
import os
import re
import shutil
import sys
import zipfile
from alive_progress import alive_bar
from numpy import byte
import click
import pymem
import pandas as pd
import requests

INDEX_PATTERN = bytes.fromhex('49 4E 44 58 10 00 00 00')    # INDX block start
TEXT_PATTERN = bytes.fromhex('54 45 58 54 10 00 00')        # TEXT block start
END_PATTERN = bytes.fromhex('46 4F 4F 54 10 00 00')         # FOOT block start
HEX_DICT = 'hex_dict.csv'

def instantiate(exe):
    '''Instantiates a pymem instance that attaches to an executable.'''
    global PY_MEM  # pylint: disable=global-variable-undefined
    global HANDLE  # pylint: disable=global-variable-undefined

    try:
        PY_MEM = pymem.Pymem(exe)
        HANDLE = PY_MEM.process_handle
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
    handle: int, pattern: bytes, multiple: bool, *, index_pattern_list,
    start_address = 0, end_address = 0x7FFFFFFF
    ):
    '''
    Scans the entire virtual memory space for a handle and returns addresses
    that match the given byte pattern.
    '''
    next_region = start_address
    while next_region < end_address:
        next_region, found = pymem.pattern.scan_pattern_page(
                                handle, next_region, pattern,
                                return_multiple = multiple)
        if found and multiple:
            index_pattern_list.append(found)
        elif found and not multiple:
            return found

def read_bytes(address, byte_count):
    '''Reads the given number of bytes starting at an address.'''
    return PY_MEM.read_bytes(address, byte_count)

def jump_to_address(handle, address, pattern):
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
    return None

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
                print('String too long. Please fix and try again.')
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
        sys.exit(
            click.secho(
                f'Failed to get latest files from weblate.\nMessage: {e}',
                fg='red'
            )
        )

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
                archive.extract(file, 'hex/files/')
                name = os.path.splitext(os.path.basename(file))
                shutil.move(
                    f'hex/files/{file}',
                    f'hex/{name[0]}{name[1]}'
                )

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
    address_scan(HANDLE, INDEX_PATTERN, True, index_pattern_list = index_pattern_list)
    data_frame = pd.read_csv(HEX_DICT, usecols = ['file', 'hex_string'])

    with alive_bar(len(__flatten(index_pattern_list)),
                                title='Translating..',
                                spinner='pulse',
                                bar='bubbles',
                                length=20) as increment_progress_bar:
        for address in __flatten(index_pattern_list):
            increment_progress_bar()
            hex_result = __split_string_into_spaces(read_bytes(address, 64).hex().upper())
            csv_result = __flatten(data_frame[data_frame.hex_string == hex_result].values.tolist())
            if csv_result != []:
                file = __parse_filename_from_csv_result(csv_result)
                hex_to_write = bytes.fromhex(generate_hex(file))
                start_addr = jump_to_address(HANDLE, address, TEXT_PATTERN)
                if start_addr:
                    start_addr = start_addr + 14
                    result = type(byte)
                    while True:
                        start_addr = start_addr + 1
                        result = read_bytes(start_addr, 1)
                        if result != b'\x00':
                            start_addr = start_addr - 1
                            break

                    pymem.memory.write_bytes(HANDLE, start_addr, hex_to_write, len(hex_to_write))

    click.secho('Done. Continuing to scan for changes. Minimize this window and enjoy!', fg='green')

def reverse_translate():
    '''Translates the game back into Japanese.'''
    instantiate('DQXGame.exe')

    index_pattern_list = []
    address_scan(HANDLE, INDEX_PATTERN, True, index_pattern_list = index_pattern_list)
    data_frame = pd.read_csv(HEX_DICT, usecols = ['file', 'hex_string'])

    with alive_bar(len(__flatten(index_pattern_list)),
                                title='Untranslating..',
                                spinner='pulse',
                                bar='bubbles',
                                length=20) as increment_progress_bar:
        for address in __flatten(index_pattern_list):
            increment_progress_bar()
            hex_result = __split_string_into_spaces(read_bytes(address, 64).hex().upper())
            csv_result = __flatten(data_frame[data_frame.hex_string == hex_result].values.tolist())
            if csv_result != []:
                file = __parse_filename_from_csv_result(csv_result)

                ja_hex_to_write = ''

                data = __read_json_file(file, 'en')
                for item in data:
                    key = list(data[item].items())[0][0]
                    if re.search('^clarity_nt_char', key):
                        ja = '00'
                    elif re.search('^clarity_ms_space', key):
                        ja = '00e38080'
                    else:
                        ja = '00' + key.encode('utf-8').hex()

                    ja = ja.replace('7c', '0a')
                    ja = ja.replace('5c74', '09')
                    ja_hex_to_write += ja

                start_addr = jump_to_address(HANDLE, address, TEXT_PATTERN)
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
                        HANDLE, start_addr, data, len(data))

def scan_for_ad_hoc_game_files():
    '''
    Continuously scans the DQXGame process for known addresses
    that are only loaded 'on demand'. Will pass the found
    address to translate().
    '''
    instantiate('DQXGame.exe')

    index_pattern_list = []
    address_scan(HANDLE, INDEX_PATTERN, True, index_pattern_list = index_pattern_list)
    data_frame = pd.read_csv(HEX_DICT, usecols = ['file', 'hex_string'])

    for address in __flatten(index_pattern_list):  # pylint: disable=too-many-nested-blocks
        hex_result = __split_string_into_spaces(read_bytes(address, 64).hex().upper())
        csv_result = __flatten(data_frame[data_frame.hex_string == hex_result].values.tolist())
        if csv_result != []:
            file = __parse_filename_from_csv_result(csv_result)
            if 'adhoc' in file:
                hex_to_write = bytes.fromhex(generate_hex(file))
                start_addr = jump_to_address(HANDLE, address, TEXT_PATTERN)
                if start_addr:
                    start_addr = start_addr + 14
                    result = type(byte)
                    while True:
                        start_addr = start_addr + 1
                        result = read_bytes(start_addr, 1)
                        if result != b'\x00':
                            start_addr = start_addr - 1
                            break

                    pymem.memory.write_bytes(HANDLE, start_addr, hex_to_write, len(hex_to_write))

def scan_for_names(byte_pattern):
    '''
    Continuously scans the DQXGame process for known addresses
    that are related to a specific pattern to translate names.
    '''
    instantiate('DQXGame.exe')

    index_pattern_list = []
    address_scan(HANDLE, byte_pattern, True, index_pattern_list = index_pattern_list)

    for address in __flatten(index_pattern_list):
        determine_bytes = read_bytes(address - 3, 2)

        if determine_bytes == b'\x5C\xBA':
            data = __read_json_file('monsters', 'en')
            name_addr = address + 9
            end_addr = address + 9
        elif determine_bytes == b'\x2C\xCC':
            data = __read_json_file('npc_names', 'en')
            name_addr = address + 9
            end_addr = address + 9
        else:
            continue

        byte_codes = [
            b'\xE3',
            b'\xE4',
            b'\xE7',
            b'\xE8',
            b'\xE9'
        ]

        if read_bytes(name_addr, 1) not in byte_codes:
            continue

        name_hex = bytearray()
        while True:
            result = read_bytes(end_addr, 1)
            end_addr = end_addr + 1
            if result == b'\x00':
                end_addr = end_addr - 1   # Remove the last 00
                bytes_to_write = end_addr - name_addr
                break

            name_hex += result

        name = name_hex.decode('utf-8')
        for item in data:
            key, value = list(data[item].items())[0]
            if re.search(f'^{name}+$', key):
                if value:
                    pymem.memory.write_bytes(HANDLE, name_addr, str.encode(value), bytes_to_write)
                    print(f'{value} found.')

def dump_all_game_files():  # pylint: disable=too-many-locals
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

    for folder in directories:
        Path(folder).mkdir(parents=True, exist_ok=True)

    data_frame = pd.read_csv(HEX_DICT, usecols = ['file', 'hex_string'])

    index_pattern_list = []
    address_scan(
        HANDLE, INDEX_PATTERN, True, index_pattern_list = index_pattern_list)

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
            start_addr = jump_to_address(HANDLE, address, TEXT_PATTERN)
            if start_addr is not None:
                end_addr = jump_to_address(HANDLE, start_addr, END_PATTERN)
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
                        json_data_ja = __format_to_json(jsondata_ja, line, 'ja', number)
                        json_data_en = __format_to_json(jsondata_en, line, 'en', number)
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
                        data_frame[data_frame.hex_string == hex_result].values.tolist())
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

    for filename in os.listdir('hyde_json_merge/src'):
        os.system(f'hyde_json_merge\json-conv.exe -s hyde_json_merge/src/{filename} -d hyde_json_merge/dst/{filename} -o hyde_json_merge/out/{filename}')  # pylint: disable=anomalous-backslash-in-string,line-too-long

def __read_json_file(base_filename, region_code):
    with open(f'json/_lang/{region_code}/{base_filename}.json', 'r', encoding='utf-8') as json_data:
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

def __split_string_into_spaces(string):
    '''
    Breaks a string up by putting spaces between every two characters.
    Used to format a hex string.
    '''
    return " ".join(string[i:i+2] for i in range(0, len(string), 2))

def __delete_folder(folder):
    '''Deletes a folder and all subfolders.'''
    shutil.rmtree(folder, ignore_errors=True)

def __parse_filename_from_csv_result(csv_result):
    '''Parse the filename from the supplied csv result.'''
    return os.path.splitext(os.path.basename(csv_result[0]))[0].strip()
