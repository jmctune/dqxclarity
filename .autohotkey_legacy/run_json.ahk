#SingleInstance, Off
#NoTrayIcon
#Include <classMemory>
#Include <convertHex>
#Include <JSON>
#Include <hashCheck>

SetBatchLines, -1

;; don't let user run this script directly
if A_Args.Length() < 1
{
    MsgBox Don't run this directly. Run dqxclarity.exe instead.
    ExitApp
}

;; instantiate memory object
dqx := new _ClassMemory("ahk_exe DQXGame.exe", "", hProcessCopy)

if !isObject(dqx)
  ExitApp

;; mark FileRead operations as UTF-8
FileEncoding UTF-8

;; read incoming arguments
fileName := A_Args[1]
start_addr := A_Args[2]
rebuild := A_Args[3]

;; if the checksum doesn't match, parse the json and re-create the hex
if (rebuild = "true")
{
  ;; read json file
  FileRead, jsonData, %fileName%
  data := "[" . jsonData . "]" ;; json lib requires [] structure
  data := JSON.Load(data)

  ;; iterate over all json objects in strings[]
  en_hex_to_write :=
  for _, subarray in data.1
  {
    for k, v in subarray
    {
      ;; handle special codes generated from dump
      if InStr(k, "clarity_nt_char")
        en := "00"
      else if InStr(k, "clarity_ms_space")
        en := "00e38080"
      else
      {
        ;; Convert utf-8 strings to hex
        jp := 00 . convertStrToHex(k)
        jp := RegExReplace(jp, "\r\n", "")
        jp_raw := k
        jp_len := StrLen(jp)

        ;; we want to make the length of our JP hex string the same as what we're inputting.
        ;; if we have a word not translated, we want to put the japanese back into the string
        if (v = "")
        {
          en := jp
          en_len := jp_len
        }
        else
        {
          en := 00 . convertStrToHex(v)
          en := RegExReplace(en, "\r\n", "")
          en_raw := v
          en_len := StrLen(en)
        }

        ; If en_len is longer than the jp_len, we'll get stuck in an
        ; infinite loop until we OOM, so check this here.
        if (en_len > jp_len)
        {
          component := A_ScriptDir . "\" . fileName
          SplitPath, component,,,,bareFileName,
          MsgBox, 4,,String too long. Please fix and try again.`nFile: %1%`nJP string: %jp_raw%`nEN string: %en_raw%`n`nDo you want to automatically search for the translation in weblate?
          IfMsgBox Yes
          {
            webpage := "https://weblate.ethene.wiki/translate/dragon-quest-x/" . bareFileName . "/en/?offset=1&q=" . jp_raw . "&sort_by=-priority%2Cposition&checksum="
            Run, %webpage%
          }
          ExitApp
        }

        ;; A lot of dialog text has spaces and line breaks in them, so we need to handle
        ;; these differently as using spaces as line breaks won't work here. This replaces
        ;; the pipe ('|') with a line break and the \t (tab) char with the appropriate value.
        jp := StrReplace(jp, "7c", "0a")  ;; pipe replace with line break
        jp := StrReplace(jp, "5C 74", "09")  ;; \t replace with tab
        en := StrReplace(en, "7c", "0a")  ;; pipe replace with line break
        en := StrReplace(en, "5C 74", "09")  ;; \t replace with tab

        ;; Add null terms until the length of the en string matches the jp string.
        if (jp_len != en_len)
        {
          Loop
          {
            en .= 00
            new_len := StrLen(en)
          }
          Until ((jp_len - new_len) == 0)
        }
      }

      ;; write the hex to our string
      en_hex_to_write .= en

    }
  }

  ;; write finished hex to file, calculate md5 checksum and also write to file
  SplitPath, fileName,,,, name_no_ext
  newChecksum := hashCheck(fileName)
  FileDelete, hex/checksums/%name_no_ext%.md5
  FileAppend, %newChecksum%, hex/checksums/%name_no_ext%.md5
  FileDelete, hex/files/%name_no_ext%.hex
  FileAppend, %en_hex_to_write%, hex/files/%name_no_ext%.hex
}
else
{
  ;; no need to rebuild hex file as checksum matches
  SplitPath, fileName,,,, name_no_ext
  FileRead, en_hex_to_write, hex/files/%name_no_ext%.hex
}

;; huge strings can cause a stack overflow when passing to writeBytes.
;; if our string is > 100000 characters, break it up into chunks and write
;; the chunks one segment at a time
if StrLen(en_hex_to_write) > "100000"
{
  ;; start of number of characters to grab from the string
  start_str := 1
  Loop
  {
    segment := SubStr(en_hex_to_write, start_str, 100000)

    if (segment = "")
      break  ;; get out of the loop as we've completed iterating through the string

    dqx.WriteBytes(start_addr, segment)

    ;; increment next set of text to iterate through
    start_str := start_str + 100000  ;; process next 100000 characters
    start_addr := start_addr + 50000 ;; 1 byte is 2 characters. as we process 100000 chars, we're writing 50000 bytes, so jump forward 50000 addresses
  }
}
else
  dqx.writeBytes(start_addr, en_hex_to_write)

ExitApp