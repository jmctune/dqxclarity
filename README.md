# dqxclarity

[Discord](https://discord.gg/bVpNqVjEG5)

Translates the command menu and other misc. text into English for the popular game "Dragon Quest X".

![#f03c15](https://via.placeholder.com/15/f03c15/000000?text=+)
**NOTE: I forfeit any responsibility if you receive a warning, a ban or a stern talking to while using this program. dqxclarity alters process memory, but only for the intent of allowing English-speaking players to read Japanese menus. No malicious activities are being performed with dqxclarity. The goal of this application is simply to translate the game's UI for non-Japanese fluent players to enjoy.**

![#f03c15](https://via.placeholder.com/15/f03c15/000000?text=+)
**The way this is being done is not currently very efficient and can be slow to run each time. This is a work in progress of a few days worth of work that I wanted to get out there and share for those that may be considering giving Dragon Quest X a shot.**

In action: https://imgur.com/ne10wiG

## How to use

Download the latest version of `dqxclarity` from the [releases](https://github.com/jmctune/dqxclarity/releases) section. Open a fresh instance of Dragon Quest X and run `dqxclarity.exe`. A window will open notifying you of what it's doing. On most machines, it seems to take anywhere between 50-120 seconds to run. In its current state, this number will only increase as more text is added, but tuning this number down is being investigated.

**Ensure you only run dqxclarity one time per game session. Running more than once will not hurt, but will not do you any good either.**

**You might see untranslated menu items when running from time to time. Yes, it's buggy and yes, I'm aware. Be thrilled it's in the state it's in now -- it will eventually get fixed.**

You'll probably see `problem.txt`, `address.txt` and `times.txt` pop up in that folder. Ignore them. Debug logs. If I ask for them, there they are.

## How it works

In the `json` folder is a structure of Japanese and English translated text. The Japanese text is convered from a utf-8 string to hex, then searched for in the active process's memory. When found, it replaces the hex values with its English equivalent.

As an example, with a structure like the following:

```
[
  {
    "jp_string": "冒険をする",
    "en_string": "Open Adventure"
  }
]
```

`jp_string` is converted to a utf-8 hex string with the `convertStrToHex()` function, as well as the `en_string` value.

Strings are prepended and appended with `00` (null terminators) as this seems to be a reliable way to find the menu items.

There are a few different json keys that can change the behavior of how the script operates. As every string isn't created equally in memory, sometimes you need to alter its behavior. The following flags are also applicable:

`ignore_first_term`: Boolean. Don't add the first null terminator to the hex'd value.<br>
`ignore_last_term`: Boolean. Don't add the last null terminator to the hex'd value.<br>
`line_break`: In `jp_string`, replace spaces with `0a` (line break). In `en_string`, replace "|" characters with `0a`. This is typically used for menu descriptions.<br>
`loop_count`: Integer. If there is more than one match (you can verify with CE), you will want to iterate over all of the results to replace all instances of that match. By default, it only finds the first match and moves on, but a `loop_count` of 2 would find the first match, then continue scanning from the last found memory address + 1.<br>

All of the above flags are optional, but `jp_string` and `en_string` are mandatory.

## How to contribute

Thanks for considering to contribute. If you choose to, there are several menu items, menu descriptions, spells and skills that still need to be translated. Additionally, if you can read Japanese, accurate translations are better. No "coding" is required -- just need to be able to understand how the json format works.

With the way this script works, exact translations sometimes won't work -- and here's why:

Suppose I have the text "冒険をする". Each Japanese character consists of 3 bytes of text (冒, 険, を, す, る) equaling 15 bytes total. In the English alphabet, each character uses 1 byte of text (O, p, e, n, , A, d, v, e, n, t, u, r, e) equaling 14 bytes total. The number of English bytes cannot exceed the number of Japanese bytes or there will be trouble. When looking to translate, sometimes you may need to think of shorter or similar words to make the text fit.

When translating descriptions in the command menu (the text on the side of the command menu that describes what the menu item does), each line break needs a space in the Japanese string and a pipe ("|") in the English. Here's an example:

```
[
  {
    "line_break": true,
    "jp_string": "フレンドや チームメンバーに かきおきを書く",
    "en_string": "Write a note to|a friend or|team member."
  }
]
```

In-game, "フレンドや", "チームメンバーに", and "かきおきを書く" are read top to bottom. But because this is a full sentence separated by line breaks, the spaces are replaced with the line break character. For Japanese, ensure you use spaces and for the English, ensure you separate the words with pipe characters. Make sure you don't exceed the character limit (take the number of Japanese characters and multiply it by 3. Don't exceed this many characters when typing it into English, but you can match it).

The format should match what the rest of the files look like. Pay attention to spaces (no tabs) and keep everything indented the same (two spaces per indent).

Preferably, you would fork this repo and submit a pull request, but if you're unfamiliar with git, you can provide your json changes to the #clarity-discussion channel and get them merged.

These are the things that are known to work and need translating:

- All class talent trees (just the actual skill/spell name). Categories and skill/spell descriptions will not currently work with dqxclarity
- Command menu items (Mostly things in Misc and Beastiary)
- Command menu descriptions
- Any untranslated items in the battle menus

If it's not on this list, don't worry about it as dqxclarity probably can't consistently change it.
