import time
import sys
from loguru import logger
from memory import (
    read_bytes,
    write_bytes,
    get_base_address,
    get_ptr_address,
    pattern_scan
)
from signatures import (
    loading_screen_active,
    loading_screen_offsets,
    cutscene_pattern
)

def load_unload_hooks(hook_list: list, debug: bool):
    '''
    Load/unload hooks based on conditionals.

    DQX does a check against what's in memory against what's in the binary. If it doesn't match,
    the client will crash with INVALID_CALL_1. This function will unload active hooks in the event
    of a loading screen and load them back when the game returns.

    All hooks being passed to this function should be in a dict.
    '''
    if not debug:
        logger.remove()
        logger.add(sys.stderr, level="INFO")

    base_address = get_base_address()
    loading_screen_addr = get_ptr_address(base_address + loading_screen_active, loading_screen_offsets)
    cutscene_addr = pattern_scan(cutscene_pattern, module='DQXGame.exe') - 212

    state = 'hook'
    cutscene_state = 'hook'

    def hook_cutscene(hook_state: str):
        '''
        If cutscene hooks are regularly active, they will cause dialog to double translate.
        Only enable them when we're in an actual cutscene
        '''
        cutscene_dict = [d for d in hook_list if d['hook_name'] == 'cutscene_detour']
        cutscene_adhoc_dict = [d for d in hook_list if d['hook_name'] == 'cutscene_file_dump_detour']
        
        if hook_state == 'orig':
            if cutscene_dict != []:
                write_bytes(cutscene_dict[0]['detour_address'], cutscene_dict[0]['original_bytes'])
            if cutscene_adhoc_dict != []:
                write_bytes(cutscene_adhoc_dict[0]['detour_address'], cutscene_adhoc_dict[0]['original_bytes'])
        elif hook_state == 'hook':
            if cutscene_dict != []:
                write_bytes(cutscene_dict[0]['detour_address'], cutscene_dict[0]['hook_bytes'])
            if cutscene_adhoc_dict != []:
                write_bytes(cutscene_adhoc_dict[0]['detour_address'], cutscene_adhoc_dict[0]['hook_bytes'])

    while True:
        try:
            loading_byte = read_bytes(loading_screen_addr, 2)
            cutscene_bytes = read_bytes(cutscene_addr, 4)
        except:
            raise Exception('Unable to interact with DQX. Please relaunch both DQX and this program to try again.')

        try:
            # not in a loading screen
            good_loading_values = [
                b'\xB8\x0B',  # 3000
                b'\xD0\x07'   # 2000
            ]
            # in a loading screen
            bad_loading_values = [
                b'\xF4\x01'  # 500
            ]
            # integrity checks are done on all loading screens, so make sure hooks are unloaded
            if loading_byte not in good_loading_values:
                if state == 'hook':
                    for hook in hook_list:
                        write_bytes(hook['detour_address'], hook['original_bytes'])
                    state = 'orig'
                    cutscene_state = 'orig'
                    logger.debug('Hooks unloaded for loading screen.')
            # put the hooks back as we aren't loading anymore
            elif loading_byte in good_loading_values and state == 'orig':
                for hook in hook_list:
                    write_bytes(hook['detour_address'], hook['hook_bytes'])
                state = 'hook'
                cutscene_state = 'orig'
                hook_cutscene(cutscene_state)
                logger.debug('Hooks loaded.')

            # cutscene management
            if loading_byte not in good_loading_values and cutscene_bytes != b'\x00\x00\x00\x00' and cutscene_state == 'orig':  # cutscene is active
                logger.debug('Cutscene detected.')
                for hook in hook_list:
                    write_bytes(hook['detour_address'], hook['original_bytes'])
                state = 'orig'
                cutscene_state = 'orig'
                # give cutscene a few seconds to get passed the loading screen and load.
                # if user skips cutscene within first 5~ seconds, don't load the cutscene hooks
                for i in range(500):
                    time.sleep(0.01)
                    cutscene_status = read_bytes(cutscene_addr, 4)
                    if i == 499:
                        cutscene_state = 'hook'
                        hook_cutscene(cutscene_state)
                        logger.debug('Cutscene hooks loaded.')
                    elif cutscene_status != b'\x00\x00\x00\x00' and loading_byte not in good_loading_values:
                        continue
                    else:
                        logger.debug('Cutscene skip was detected.')
                        time.sleep(3)
                        break
                while True:
                    loading_byte = read_bytes(loading_screen_addr, 2)
                    cutscene_status = read_bytes(cutscene_addr, 4)
                    if loading_byte in bad_loading_values or cutscene_status == b'\x00\x00\x00\x00':
                        for hook in hook_list:
                            write_bytes(hook['detour_address'], hook['original_bytes'])
                        state = 'orig'
                        cutscene_state = 'orig'
                        logger.debug('Cutscene is finished. Unloaded hooks.')
                        break
                    else:
                        time.sleep(0.01)
            elif loading_byte in good_loading_values and cutscene_bytes == b'\x00\x00\x00\x00' and cutscene_state == 'hook':  # cutscene is inactive
                state = 'hook'
                cutscene_state = 'orig'
                for hook in hook_list:
                    write_bytes(hook['detour_address'], hook['hook_bytes'])
                hook_cutscene(cutscene_state)  # don't leave cutscene loaded to not interfere with regular dialog
                logger.debug('Hooks loaded.')

            time.sleep(0.01)
        except:
            for hook in hook_list:
                write_bytes(hook['detour_address'], hook['original_bytes'])
            sys.exit()