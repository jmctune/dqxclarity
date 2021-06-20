# dqxclarity <a href="http://weblate.ethene.wiki/engage/dragon-quest-x/">
<img src="http://weblate.ethene.wiki/widgets/dragon-quest-x/en/svg-badge.svg" alt="Translation status" />
</a>

[Discord](https://discord.gg/bVpNqVjEG5)

Translates the command menu and other misc. text into English for the popular game "Dragon Quest X".

![#f03c15](https://via.placeholder.com/15/f03c15/000000?text=+)
**NOTE: I forfeit any responsibility if you receive a warning, a ban or a stern talking to while using this program. dqxclarity alters process memory, but only for the intent of allowing English-speaking players to read Japanese menus. No malicious activities are being performed with dqxclarity. The goal of this application is simply to translate the game's UI for non-Japanese fluent players to enjoy.**

In action:

https://user-images.githubusercontent.com/17505625/120054067-5e995f80-bff3-11eb-9bc6-77595985eb10.mp4

## How to use

Download the latest version of `dqxclarity` from the [releases](https://github.com/jmctune/dqxclarity/releases) section. Open a fresh instance of Dragon Quest X and run `dqxclarity.exe` (don't run any other `.exe` files directly). Wait for things to finish translating and you're done. 

## How it works

In the `json\_lang\en` folder are several files with a structure of Japanese and English text. The Japanese and English text are converted from a utf-8 string to hex. The Japanese and English text are compared against to ensure that the English text is not longer than the Japanese text. If everything looks good, it's added to a master hex variable. Once a file has been fully processed, it writes that entire hex string to memory.

As an example, with a structure like the following:

```
{
  "冒険をする": "Open Adventure"
}
```

`冒険をする` is converted to a utf-8 hex string with the `convertStrToHex()` function, as well as the `Open Adventure` value.

Strings are prepended with `00` (null terminators) as this begins the string.

## How to contribute

Thanks for considering to contribute. If you choose to, there is tons of work to do.  If you can read Japanese, accurate translations are better. No coding experience is required -- you just need to be able to understand a few key rules as seen below.

With the way this script works, exact translations sometimes won't work -- and here's why:

Suppose I have the text "冒険をする". Each Japanese character consists of 3 bytes of text (冒, 険, を, す, る) equaling 15 bytes total. In the English alphabet, each character uses 1 byte of text (O, p, e, n, , A, d, v, e, n, t, u, r, e) equaling 14 bytes total. The number of English bytes cannot exceed the number of Japanese bytes or there will be trouble. When looking to translate, sometimes you may need to think of shorter or similar words to make the text fit.

When translating lines that have line breaks (sentences that may run on to the next line), the Japanese text will have a pipe ("|") character to announce this. If you see a pipe character in the Japanese text, it's guaranteed you are going to want to split up its English equivalent so the text fits. Here's an example:

```
{
    "フレンドや|チームメンバーに|かきおきを書く": "Write a note to|a friend or|team member."
}
```

In-game, "フレンドや", "チームメンバーに", and "かきおきを書く" are read top to bottom. We use the pipe character to tell Clarity to enter this text on the next line. This is important to understand for your text to look correct in game.

**Make sure you don't exceed the character limit using the system above (usually, you can take the number of Japanese characters and multiply it by 3. Don't exceed this many characters when typing it into English, but you can match it).** Failure to ignore this will cause errors in Clarity and the file won't translate.

If you would like to contribute, please jump on our Discord (link seen at the top) and let's talk in #clarity-discussion.

## Clarity is seen as a virus by Windows. What gives?

Clarity is scanning and writing process memory, which is similar behavior to what viruses may do, hence the auto flag from Windows. This program is not malicious and the alert can be safely disregarded. I'd suggest [whitelisting](https://support.microsoft.com/en-us/windows/add-an-exclusion-to-windows-security-811816c0-4dfd-af4a-47e4-c301afe13b26) your entire `dqxclarity` folder in this case.
