import os
import sys
from json import dumps

def loading_shellcode(
    eax_address: str,
    state_address: str,
    hook_list: list) -> str:
    '''
    Returns shellcode for hooking to a loading function.

    eax_address: Where loading state can be found.
    state_address: Where to write current eax address and state of this hook (0/1).
    hook_list: List of hooks, their locations and their bytes to revert.
    '''
    local_paths = dumps(sys.path).replace('\\', '\\\\')
    working_dir = dumps(os.getcwd()).replace('\\', '\\\\')

    shellcode = fr"""
import sys
import os
from traceback import format_exc
from os import chdir

local_paths = {local_paths}
working_dir = {working_dir}
sys.path = local_paths
chdir(working_dir)

try:
    from memory import read_bytes, write_bytes
    from hook import pack_to_int, unpack_to_int

    state_address = {state_address}
    eax_address = unpack_to_int({eax_address})[0]
    eax_address = eax_address + 4

    # detach all hooks
    if read_bytes(eax_address, 4) == b'\x00\x00\x00\x00': # we are in combat. no need to unhook
        for hook in {hook_list}:
            write_bytes(hook['detour_address'], hook['original_bytes'])

        # mark state byte as inactive
        state_byte = b'\x00'
        
        write_bytes(state_address, state_byte)

        bytecode = (pack_to_int(eax_address))
        write_bytes(state_address + 1, bytecode)

except:
    with open('out.log', 'a+') as f:
        f.write(format_exc())
    """

    return str(shellcode)
