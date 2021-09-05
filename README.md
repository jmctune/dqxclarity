# dqxclarity <a href="http://weblate.ethene.wiki/engage/dragon-quest-x/">
<img src="http://weblate.ethene.wiki/widgets/dragon-quest-x/en/svg-badge.svg" alt="Translation status" />
</a>

[Discord](https://discord.gg/M8cBZPUN7p)

Translates the command menu and other misc. text into English for the popular game "Dragon Quest X".

![#f03c15](https://via.placeholder.com/15/f03c15/000000?text=+)
**NOTE: I forfeit any responsibility if you receive a warning, a ban or a stern talking to while using this program. `dqxclarity` alters process memory, but only for the intent of allowing English-speaking players to read Japanese menus. No malicious activities are being performed with `dqxclarity`. The goal of this application is simply to translate the game's UI for non-Japanese speaking players to enjoy.**

In action:

https://user-images.githubusercontent.com/17505625/120054067-5e995f80-bff3-11eb-9bc6-77595985eb10.mp4

## How to use

- Download the latest version of `dqxclarity` from the [releases](https://github.com/jmctune/dqxclarity/releases) section
- Open a fresh instance of Dragon Quest X (preferably from the starting screen where you choose your adventure slot)
- Run `dqxclarity.exe`
- Minimize the window that opened as things will continue translating while you're playing

### Advanced

`dqxclarity` was written as a command-line tool, so there are a few advanced things it can do:

```txt
Usage: dqxclarity.exe [OPTIONS]

Options:
  -w, --update-weblate     Grabs the latest files from the weblate branch and
                           then translates.
  -d, --dump-game-data     ADVANCED: Dumps all found game data and converts
                           each file into nested json. Output can be found in
                           the `game_file_dumps` directory. Useful when the
                           game patches.
  -m, --migrate-game-data  ADVANCED: Migrate existing json files into new
                           dumped files. Make sure you dump the game files
                           first with `--dump-game-data`. Output can be found
                           in the `hyde_json_merge/out` directory. You are
                           responsible for fixing the differences.
  --help                   Show this message and exit.
```

Users wanting to get the latest files at any given moment will want to create a shortcut and pass the `-w` flag to the executable to update from the weblate branch. I'd suggest reading [this](https://www.digitalcitizen.life/shortcut-arguments-parameters-windows/) if you are unfamiliar with creating shortcuts in Windows.

The other two flags are advanced features that are used to both generate and migrate json. You will likely never use these unless you're a savvy user and interested in contributing to the json inventory of files.

## But I'm a savvy user and want to contibute new dump files!

Sweet. In that case, here's how this works.

`dqxclarity` performs a regular translation of all known static files that are loaded into memory on instance creation. On top of that, dynamic (adhoc) actions that happen inside the game (opening menus, talking to certain menu-driven NPCs, interacting with casino objects like roulette, slots, etc) will load additional game files that aren't in that initial static file list. `dqxclarity` will detect these "adhoc" changes in the game, but not automatically. You will need to trigger an event like one previously listed, then run `dqxclarity` with the `-d` or `--dump-game-data` flag to see if there is a change that hasn't been recognized. Make sure not to run `dqxclarity` prior to performing a dump as you won't have an accurate, Japanese dump (and may get errors).

If a new file has been detected during the dump, you will see a message similar to the following:

```
Unknown file found: 1.json
```

These unknown files are placed in `game_file_dumps\unknown\en` and `game_file_dumps\unknown\ja` and additionally, an entry consisting of the beginning of that game file is found in `game_file_dumps\consider_master_dict.csv`. I will need all of these files to be able to add them to the master `hex_dict.csv` file that can be used for everyone to start being able to translate these files. There's a possibility that multiple new files were found - make sure you rename the json files and the entry in `consider_master_dict.csv` to an appropriate name for the file. You can send them to me in #translation-discussion or you can submit a PR and I'll grab them that way. If the program finds multiple new files, but they look identical, it just means that there were multiple references of that file in memory that were found. Ignore the duplicate and only focus on one of them.

## How does this thing work

In the `json\_lang\en` folder are several files with a structure of Japanese and English text. These files were dumped as hex from game memory, then converted from hex -> utf-8, then formatted into a nested JSON structure for parsing. The values are then converted back into hex and written back to the same place it was dumped from.

## How to contribute to the translations

Thanks for considering to contribute. If you choose to, there is tons of work to do. If you can read Japanese, accurate translations are better. No coding experience is required -- you just need to be able to understand a few key rules as seen below.

With the way this script works, exact translations sometimes won't work -- and here's why:

Suppose I have the text "冒険をする". Each Japanese character consists of 3 bytes of text (冒, 険, を, す, る) equaling 15 bytes total. In the English alphabet, each character uses 1 byte of text (O, p, e, n, , A, d, v, e, n, t, u, r, e) equaling 14 bytes total. The number of English bytes cannot exceed the number of Japanese bytes or there will be trouble. When looking to translate, sometimes you may need to think of shorter or similar words to make the text fit.

When translating lines that have line breaks (sentences that may run on to the next line), the Japanese text will have a pipe ("|") character to announce this. If you see a pipe character in the Japanese text, it's guaranteed you are going to want to split up its English equivalent so the text fits. Here's an example:

```
{
    "フレンドや|チームメンバーに|かきおきを書く": "Write a note to|a friend or|team member."
}
```

In-game, "フレンドや", "チームメンバーに", and "かきおきを書く" are read top to bottom. We use the pipe character to tell `dqxclarity` to enter this text on the next line. This is important to understand for your text to look correct in game.

**Make sure you don't exceed the character limit using the system above (usually, you can take the number of Japanese characters and multiply it by 3. Don't exceed this many characters when typing it into English, but you can match it).** Failure to ignore this will cause errors in `dqxclarity` and the file won't translate.

Additionally, there are special tags that start with `clarity_` that should **never** be altered. If you're caught altering these, I may revoke your right to contribute. Leave them alone!

If you would like to contribute, please jump on our Discord (link seen at the top) and let's talk in #translation-discussion.

## But what are those `clarity_` lines for?

When the loaded text is dumped from memory, some strings have additional null terminators ('00') or tab characters that are included in the json. As the text has to be put back with the **exact** number of characters, the extra null terminators and tab characters have to be accounted for. These are basically placeholder strings that are handled and converted appropriately when `dqxclarity` is run.

## `dqxclarity` is seen as a virus by Windows. What gives?

`dqxclarity` is scanning and writing process memory, which is similar behavior to what viruses may do, hence the auto flag from Windows. This program is not malicious and the alert can be safely disregarded. I'd suggest [whitelisting](https://support.microsoft.com/en-us/windows/add-an-exclusion-to-windows-security-811816c0-4dfd-af4a-47e4-c301afe13b26) your entire `dqxclarity` folder in this case.

## Contributing to development

Requirements for building:
- make (`choco install make`)
- Python 3.9.6 64-bit

Building:
- Create a virtual environment for yourself inside the `dqxclarity` folder
  - `python3 -m venv venv`
- Run `activate.ps1`
- Install dependencies with `pip install -r requirements.txt`
- Run `make build`
