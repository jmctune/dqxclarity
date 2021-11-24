'''
Python program used to translate various game UI elements for the game "Dragon Quest X".
'''

from multiprocessing import Process
import sys
import time
import click
from loguru import logger
from pymem.exception import WinAPIError
from clarity import (translate, get_latest_from_weblate,
    dump_all_game_files, scan_for_player_names,
    migrate_translated_json_data, scan_for_npc_names,
    check_for_updates)
from hook import translate_detour, inject_python_dll, cutscene_detour, cutscene_file_dump_detour
from hook_mgmt.hide_hooks import load_unload_hooks

@click.command()
@click.option('-v', '--debug', is_flag=True,
                help='''Turns on additional logging to console.''')
@click.option('-w', '--update-weblate', is_flag=True,
                help='''Grabs the latest files from the weblate branch and then translates.''')
@click.option('-c', '--communication-window', is_flag=True,
                help='''THIS IS EXPERIMENTAL. DO NOT REPORT BUGS. I PROBABLY ALREADY KNOW.
                        Translates the text in the dialog window using a live
                        translation service like DeepL or Google Translate.
                        Requires a valid account with an API key to use.''')
@click.option('-p', '--player-names', is_flag=True,
                help='''Scans for player names and changes them to their translated counterpart.''')
@click.option('-n', '--npc-names', is_flag=True,
                help='''Scans for NPC names and changes them to their translated counterpart.''')
@click.option('-u', '--disable-update-check', is_flag=True,
                help='''Disables checking for updates on each launch.''')
@click.option('-d', '--dump-game-data', is_flag=True,
                help='''ADVANCED: Dumps all found game data and converts each file into nested json.
                        Output found in `game_file_dumps` directory. Useful when the game patches.''')
@click.option('-m', '--migrate-game-data', is_flag=True,
                help='''ADVANCED: Migrates existing json files into new dumped files.
                        Make sure you dump the game files first with `--dump-game-data`.
                        Output can be found in the `hyde_json_merge/out` directory.
                        You are responsible for reconciling differences.''')

def blast_off(update_weblate=False, dump_game_data=False, migrate_game_data=False,
            disable_update_check=False, communication_window=False, player_names=False,
            npc_names=False, debug=False):
    logger.warning('Getting started. DO NOT TOUCH THE GAME OR REMOVE YOUR MEMORY CARD.')
    if dump_game_data:
        dump_all_game_files()
        sys.exit('Finished!')
    if migrate_game_data:
        migrate_translated_json_data()
        sys.exit('Migrated!')
    if update_weblate:
        click.secho('Getting latest files...', fg='green')
        get_latest_from_weblate()
    if not disable_update_check:
        check_for_updates()
    if not debug:
        logger.remove()
        logger.add(sys.stderr, level="INFO")

    translate()
    hooks = []

    try:
        if communication_window:
            inject_python_dll()
            translate_hook = translate_detour(debug)
            cutscene_hook = cutscene_detour(debug)
            cutscene_file_dump_hook = cutscene_file_dump_detour()
            hooks.append(translate_hook)
            hooks.append(cutscene_hook)
            hooks.append(cutscene_file_dump_hook)
        if player_names:
            Process(name='Player name scanner', target=scan_for_player_names, args=()).start()
        if npc_names:
            Process(name='NPC scanner', target=scan_for_npc_names, args=()).start()
        if hooks:
            Process(name='Hook manager', target=load_unload_hooks, args=(hooks, debug)).start()
    except WinAPIError:
        sys.exit(click.secho('Can\'t find DQX process. Exiting.', fg='red'))
    
    time.sleep(5)  # Give the above processes time to kick off before letting the user know to continue
    logger.info('Done! Keep this window open (minimize it) and have fun on your adventure!')

if __name__ == '__main__':
    blast_off()
