'''
Tells PyInstaller how to build executable.
'''

import PyInstaller.__main__

PyInstaller.__main__.run([
    'main.py',
    'clarity.py',
    '-F',
    '--icon=imgs/rosie.ico',
    '-ndqxclarity'
])
