import click
from clarity import translate, get_latest_from_weblate, scan_for_ad_hoc_game_files, dump_all_game_files, migrate_translated_json_data
import pymem
import sys

@click.command()
@click.option('-w', '--update-weblate', is_flag=True, help='Grabs the latest files from the weblate branch and then translates.')
@click.option('-d', '--dump-game-data', is_flag=True, help='ADVANCED: Dumps all found game data and converts each file into nested json. Output can be found in the `game_file_dumps` directory. Useful when the game patches.')
@click.option('-m', '--migrate-game-data', is_flag=True, help='ADVANCED: Migrate existing json files into new dumped files. Make sure you dump the game files first with `--dump-game-data`. Output can be found in the `hyde_json_merge/out` directory. You are responsible for fixing the differences.')
def blast_off(update_weblate, dump_game_data, migrate_game_data):
  if dump_game_data:
    dump_all_game_files()
    sys.exit('Finished!')
    
  if migrate_game_data:
    migrate_translated_json_data()
    sys.exit('Migrated!')
  
  if update_weblate:
    click.secho('Getting latest files...', fg='green')
    get_latest_from_weblate()
  
  translate()
  
  while True:
    try:
      scan_for_ad_hoc_game_files()
    except pymem.exception.WinAPIError as e:
      sys.exit(click.secho('Can\'''t find DQX process. Exiting.', fg='red'))
  
if __name__ == '__main__':
  blast_off()