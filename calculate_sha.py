'''
Gets the sha of exe and writes to file.
Used to determine if the exe has changed and will
eventually prompt user for an update.
'''

import hashlib

filename = 'dqxclarity.exe'
with open(filename,"rb") as f:
    bytes = f.read()
    readable_hash = hashlib.sha256(bytes).hexdigest();

with open(f'sha', 'w') as f:
    f.write(readable_hash)