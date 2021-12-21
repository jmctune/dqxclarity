import struct
import time
import sys
from loguru import logger
from memory import (
    read_bytes,
    write_bytes,
    pattern_scan,
    get_base_address,
    get_ptr_address
)
from signatures import (
    login_screen_active,
    login_screen_offsets,
    cutscene_pattern
)

def unpack_to_int(address: int):
    '''
    Unpacks the address from little endian and returns the appropriate bytes.
    '''
    unpacked_address = struct.unpack('<i', address)

    return unpacked_address

def load_unload_hooks(hook_list: list, state_address: int, debug: bool):
    '''
    Load/unload hooks based on conditionals.

    DQX does a check against what's in memory against what's in the binary. If it doesn't match,
    the client will crash with INVALID_CALL_1. This function will unload active hooks in the event
    of a loading screen and load them back when the game returns.

    All hooks being passed to this function should be in a dict.
    '''
    def hook_cutscene(hook_state: str):
        '''
        If cutscene hooks are regularly active, they will cause dialog to double translate.
        Only enable them when we're in an actual cutscene
        '''
        cutscene_dict = [d for d in hook_list if d['hook_name'] == 'cutscene_detour']
        cutscene_adhoc_dict = [d for d in hook_list if d['hook_name'] == 'cutscene_file_dump_detour']
        
        if cutscene_state == 'orig':
            if cutscene_dict != []:
                write_bytes(cutscene_dict[0]['detour_address'], cutscene_dict[0]['original_bytes'])
            if cutscene_adhoc_dict != []:
                write_bytes(cutscene_adhoc_dict[0]['detour_address'], cutscene_adhoc_dict[0]['original_bytes'])
        elif cutscene_state == 'hook':
            if cutscene_dict != []:
                write_bytes(cutscene_dict[0]['detour_address'], cutscene_dict[0]['hook_bytes'])
            if cutscene_adhoc_dict != []:
                write_bytes(cutscene_adhoc_dict[0]['detour_address'], cutscene_adhoc_dict[0]['hook_bytes'])

    if not debug:
        logger.remove()
        logger.add(sys.stderr, level="INFO")

    base_address = get_base_address()
    cutscene_addr = pattern_scan(cutscene_pattern, module='DQXGame.exe') - 212
    login_screen_addr = get_ptr_address(base_address + login_screen_active, login_screen_offsets)

    # loading address has 44 bytes that need to be 00 before we're clear of loading screens
    bytecode = b''
    for i in range(44):
        bytecode += b'\x00'

    logger.debug(f'Looking at {hex(cutscene_addr)} for cutscenes.')

    while True:
        try:
            state_byte = read_bytes(state_address, 1)
            login_screen_byte = read_bytes(login_screen_addr, 1)
        except:
            raise Exception('Unable to interact with DQX. Please relaunch both DQX and this program to try again.')

        try:
            # don't do anything on login screen. initializing python scripts will cause infinite login load
            if state_byte == b'\x00':  # hooks are inactive, which means loading was triggered
                logger.debug('Hooks unloaded.')
                time.sleep(1)
                packed_loading = read_bytes(state_address + 1, 4)
                unpacked_loading = unpack_to_int(packed_loading)[0]
                while True:
                    loading_bytes = read_bytes(unpacked_loading + 4, 44)
                    cutscene_bytes = read_bytes(cutscene_addr, 4)
                    if loading_bytes == bytecode:
                        if cutscene_bytes != b'\x00\x00\x00\x00':
                            logger.debug('Cutscene detected.')
                            for hook in hook_list:
                                write_bytes(hook['detour_address'], hook['hook_bytes'])
                            write_bytes(state_address, b'\x01')
                            break
                        elif cutscene_bytes == b'\x00\x00\x00\x00':
                            for hook in hook_list:
                                write_bytes(hook['detour_address'], hook['hook_bytes'])
                            logger.debug('Hooks loaded.')
                            cutscene_state = 'orig'
                            hook_cutscene(cutscene_state)
                            write_bytes(state_address, b'\x01')  # write over state byte. hooks are active again
                            break
                    else:
                        time.sleep(0.25)
            else:
                time.sleep(0.05)
        except:
            for hook in hook_list:
                write_bytes(hook['detour_address'], hook['original_bytes'])
            sys.exit()
