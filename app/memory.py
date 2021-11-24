import re
from typing import Union
import pymem, pymem.process, pymem.exception
from errors import (
    AddressOutOfRange,
    MemoryReadError,
    MemoryWriteError,
    PatternMultipleResults,
    FailedToReadAddress,
    messageBoxFatalError
)
from signatures import (
    text_pattern,
    foot_pattern,
    index_pattern
)

def dqx_mem():
    '''
    Instantiates a pymem instance.
    '''
    try:
        return pymem.Pymem('DQXGame.exe')
    except pymem.exception.ProcessNotFound:
        messageBoxFatalError('DQX not found', 'Open DQX, get to the title screen and re-launch.')

def read_bytes(address: int, size: int):
    '''
    Read n number of bytes at address.

    Args:
        address: The address to start at
        bytes_to_read: Number of bytes to read from start of address
    '''
    if address is None:
        raise FailedToReadAddress(address)

    if not 0 < address <= 0x7FFFFFFF:
        raise AddressOutOfRange(address)

    try:
        return PYM_PROCESS.read_bytes(address, size)
    except pymem.exception.MemoryReadError:
        raise MemoryReadError(address)

def write_bytes(address: int, value: bytes):
    '''
    Write bytes to memory at address.

    Args:
        address: The address to write to
        value: The bytes to write
    '''
    size = len(value)

    try:
        PYM_PROCESS.write_bytes(address, value, size)
    except pymem.exception.MemoryWriteError:
        raise MemoryWriteError(address)

def read_int(address: int):
    return PYM_PROCESS.read_int(address)

def read_string(address: int):
    '''
    Reads a string from memory at the given address.
    '''
    end_addr = address

    if end_addr is not None:
        while True:
            result = PYM_PROCESS.read_bytes(end_addr, 1)
            end_addr = end_addr + 1
            if result == b'\x00':
                bytes_to_read = end_addr - address
                break

        return PYM_PROCESS.read_string(address, bytes_to_read)

def write_string(address: int, text: str):
    '''
    Writes a string to memory at the given address.
    '''
    return PYM_PROCESS.write_string(address, text)

def pattern_scan(
    pattern: bytes, *, module: str = None, return_multiple: bool = False) -> Union[list, int]:
    '''
    Scan for a byte pattern.

    Args:
        pattern: The byte pattern to search for
        module: What module to search or None to search all
        return_multiple: If multiple results should be returned
    Raises:
        PatternFailed: If the pattern returned no results
        PatternMultipleResults: If the pattern returned multiple results and return_multple is False
    Returns:
        A list of results if return_multiple is True. Otherwise, one result.
    '''
    if module:
        module = pymem.process.module_from_name(PYM_PROCESS.process_handle, module)
        found_addresses = _scan_entire_module(PYM_PROCESS.process_handle, module, pattern)

    else:
        found_addresses = _scan_all(
            PYM_PROCESS.process_handle, pattern, return_multiple)

    if (found_length := len(found_addresses)) == 0:
        if return_multiple:
            return []
        else:
            return
    elif found_length > 1 and not return_multiple:
        raise PatternMultipleResults(f"Got {found_length} results for {pattern}")
    elif return_multiple:
        return found_addresses
    else:
        return found_addresses[0]

def scan_backwards(start_addr: int, pattern: bytes):
    '''
    From start_addr, read bytes backwards until a pattern is found.
    Used primarily for finding the beginning of an adhoc file.
    '''
    curr_addr = start_addr
    curr_bytes = bytes()
    segment_size = 120  # give us a buffer to read from
    segment_buffer_size = segment_size * 2  # prevent match from getting chopped off
    loop_count = 1
    while True:
        curr_segment = read_bytes(curr_addr, segment_size)
        curr_bytes = curr_segment + curr_bytes  # want the pattern to be read left to right, so prepending
        if len(curr_bytes) > segment_buffer_size:
            curr_bytes = curr_bytes[:-segment_size]  # keep our buffer reasonably sized
        if pattern in curr_bytes:  # found our match
            position = re.search(pattern, curr_bytes).span(0)
            return curr_addr + position[0]
        curr_addr -= segment_size
        loop_count += 1
        if loop_count * segment_size > 1000000:
            return False  # this scan is slow, so don't scan forever.

def find_first_match(start_addr: int, pattern: bytes) -> int:
    '''
    This is so dumb that this has to exist, but scan_pattern_page does not
    find patterns consistently, so we must read this byte by byte
    until we find a match. This works like scan backwards, but the other way around.
    '''
    curr_addr = start_addr
    curr_bytes = bytes()
    segment_size = 120  # give us a buffer to read from
    segment_buffer_size = segment_size * 2  # prevent match from getting chopped off
    loop_count = 1
    while True:
        curr_segment = read_bytes(curr_addr, segment_size)
        curr_bytes = curr_segment + curr_bytes
        if pattern in curr_bytes:  # found our match
            position = re.search(pattern, curr_bytes).span(0)
            return curr_addr + position[0]
        if len(curr_bytes) > segment_buffer_size:
            curr_bytes = curr_bytes[segment_size:]  # keep our buffer reasonably sized
        curr_addr += segment_size
        loop_count += 1
        if loop_count * segment_size > 1000000:
            return False  # this scan is slow, so don't scan forever.

def get_ptr_address(base, offsets):
    '''
    Gets the address a pointer is pointing to.

    Args:
        base: Base of the pointer
        offsets: List of offsets
    '''
    addr = PYM_PROCESS.read_int(base)
    for offset in offsets:
        if offset != offsets[-1]:
            addr = PYM_PROCESS.read_int(addr + offset)

    return addr + offsets[-1]

def get_base_address(name='DQXGame.exe') -> int:
    '''
    Returns the base address of a module. Defaults to DQXGame.exe.
    '''
    return pymem.process.module_from_name(PYM_PROCESS.process_handle, name).lpBaseOfDll

def get_start_of_game_text(indx_address: int) -> int:
    '''
    Returns the address of the first character of text from a loaded
    game file. This should be used when starting at an INDX address.
    '''
    address = find_first_match(indx_address, text_pattern)
    loop_count = 1
    if address:
        address += 16  # skip passed all the junk bytes
        while True:  # skip passed the padded 00's
            result = read_bytes(address, 1)
            if result != b'\x00':
                address
                break
            address += 1
            loop_count += 1
            if loop_count > 50:
                return False

        return address

def _scan_page_return_all(handle: int, address: int, pattern):
    mbi = pymem.memory.virtual_query(handle, address)
    next_region = mbi.BaseAddress + mbi.RegionSize
    allowed_protections = [
        pymem.ressources.structure.MEMORY_PROTECTION.PAGE_EXECUTE_READ,
        pymem.ressources.structure.MEMORY_PROTECTION.PAGE_EXECUTE_READWRITE,
        pymem.ressources.structure.MEMORY_PROTECTION.PAGE_READWRITE,
        pymem.ressources.structure.MEMORY_PROTECTION.PAGE_READONLY,
    ]
    if (
        mbi.state != pymem.ressources.structure.MEMORY_STATE.MEM_COMMIT
        or mbi.protect not in allowed_protections
    ):
        return next_region, None

    page_bytes = pymem.memory.read_bytes(handle, address, mbi.RegionSize)

    found = []

    for match in re.finditer(pattern, page_bytes, re.DOTALL):
        found_address = address + match.span()[0]
        found.append(found_address)

    return next_region, found

def _scan_entire_module(handle, module, pattern):
    base_address = module.lpBaseOfDll
    max_address = module.lpBaseOfDll + module.SizeOfImage
    page_address = base_address

    found = []
    while page_address < max_address:
        page_address, page_found = _scan_page_return_all(handle, page_address, pattern)
        if page_found:
            found += page_found

    return found

def _scan_all(handle: int, pattern: bytes, return_multiple: bool = False):
    next_region = 0

    found = []
    while next_region < 0x7FFFFFFF:
        next_region, page_found = _scan_page_return_all(handle, next_region, pattern)
        if page_found:
            found += page_found

        if not return_multiple and found:
            break

    return found

PYM_PROCESS = dqx_mem()
