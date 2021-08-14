import click
from clarity import translate, get_latest_from_weblate, scan_for_ad_hoc_game_files, dump_all_game_files, migrate_translated_json_data, reverse_translate, scan_for_names
from multiprocessing import Process, freeze_support
import pymem
import sys

@click.command()
@click.option('-w', '--update-weblate', is_flag=True, help='Grabs the latest files from the weblate branch and then translates.')
@click.option('-u', '--untranslate', is_flag=True, help='Translates the game back into Japanese.')
@click.option('-d', '--dump-game-data', is_flag=True, help='ADVANCED: Dumps all found game data and converts each file into nested json. Output can be found in the `game_file_dumps` directory. Useful when the game patches.')
@click.option('-m', '--migrate-game-data', is_flag=True, help='ADVANCED: Migrate existing json files into new dumped files. Make sure you dump the game files first with `--dump-game-data`. Output can be found in the `hyde_json_merge/out` directory. You are responsible for fixing the differences.')
def blast_off(update_weblate, dump_game_data, migrate_game_data, untranslate):
  if dump_game_data:
    dump_all_game_files()
    sys.exit('Finished!')
    
  if migrate_game_data:
    migrate_translated_json_data()
    sys.exit('Migrated!')
    
  if untranslate:
    reverse_translate()
    sys.exit('Untranslated!')
  
  if update_weblate:
    click.secho('Getting latest files...', fg='green')
    get_latest_from_weblate()
  
  translate()
    
  while True:
    try:
      Process(target=scan_for_ad_hoc_game_files()).start()
      Process(target=scan_for_names(
                b'\x5C\xBA.\x01....\x68\xCC.\x01', 
                'json/_lang/en/monsters.json',
                11)).start()
      Process(target=scan_for_names(
              b'\x2C\xCC.\x01....\x68\xCC.\x01',
              'json/_lang/en/npc_names.json',
              12)).start()
    except pymem.exception.WinAPIError as e:
      sys.exit(click.secho('Can\'''t find DQX process. Exiting.', fg='red'))
  
if __name__ == '__main__':
  freeze_support()  # Needed for multiprocessing support with PyInstaller
  blast_off()