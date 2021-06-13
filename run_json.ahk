#SingleInstance, Off
#NoTrayIcon
#Include <classMemory>
#Include <convertHex>
#Include <memWrite>
#Include <JSON>

SetBatchLines, -1

if (_ClassMemory.__Class != "_ClassMemory") {
  msgbox class memory not correctly installed. Or the (global class) variable "_ClassMemory" has been overwritten
  ExitApp
}

dqx := new _ClassMemory("ahk_exe DQXGame.exe", "", hProcessCopy)
Global dqx

if !isObject(dqx)
{
  msgbox Please open Dragon Quest X before running dqxclarity.
  ExitApp
  if (hProcessCopy = 0)
  {
    msgbox The program isn't running (not found) or you passed an incorrect program identifier parameter.
    ExitApp
  }
  else if (hProcessCopy = "")
  {
    msgbox OpenProcess failed. If the target process has admin rights, then the script also needs to be ran as admin. Consult A_LastError for more information.
    ExitApp
  }
}

;; Mark FileRead operations as UTF-8
FileEncoding UTF-8

;; Re-assign incoming arg
jsonToTranslate = %1%

;; Read json file
FileRead, jsonData, %jsonToTranslate%
data := "[" . jsonData . "]" ;; json lib requires [] structure
data := json.Parse(data)

;; Parse hex_dict csv to figure out where to start
Loop, Read, %A_ScriptDir%\hex_dict.csv
{
  LineNumber := A_Index
  Loop, Parse, A_LoopReadLine, CSV
  {
    if (A_LoopField = jsonToTranslate)
    {
      split := StrSplit(A_LoopReadLine, ",")
      hexStart := split[2]
      iterations := split[3]
      break
    }
  }
}

;; Iterate over all json objects in strings[]
Loop, %iterations%
{
  textHex := dqx.hexStringToPattern(hexStart)  ;; Start of TEXT block
  footAOB := [0, 0, 0, 0, 70, 79, 79, 84]  ;; End of TEXT block (FOOT)
  startAddr := dqx.processPatternScan(,,textHex*)
  endAddr := dqx.processPatternScan(startAddr,, footAOB*)

  for i, obj in data
  {
    for k, v in obj
    {
      ;; If en_string is blank, skip it
      if (v == "")
        Continue

      ;; Convert utf-8 strings to hex
      jp := 00 . convertStrToHex(k)
      jp := RegExReplace(jp, "\r\n", "")
      jp_raw := k
      jp_len := StrLen(jp)

      ;; For other languages, we want to make the length of our JP hex
      ;; string the same as what we're inputting.
      en := 00 . convertStrToHex(v)
      en := RegExReplace(en, "\r\n", "")
      en_raw := v
      en_len := StrLen(en)

      ;; If the string length doesn't match, add null terms until it does.
      if (jp_len != en_len)
      {
        ; If en_len is longer than the jp_len, we'll get stuck in an
        ; infinite loop until we OOM, so check this here.
        if (en_len > jp_len)
        {
          component := A_ScriptDir . "\" . jsonToTranslate
          SplitPath, component,,,,bareFileName,
          MsgBox, 4,,String too long. Please fix and try again.`nFile: %1%`nJP string: %jp_raw%`nEN string: %en_raw%`n`nDo you want to automatically search for the translation in weblate?
          IfMsgBox Yes
          {
            webpage := "https://weblate.ethene.wiki/translate/dragon-quest-x/" . bareFileName . "/en/?offset=1&q=" . jp_raw . "&sort_by=-priority%2Cposition&checksum="
            Run, %webpage%
          }
          continue
        }

        ;; A lot of dialog text has spaces and line breaks in them, so we need to handle
        ;; these differently as using spaces as line breaks won't work here. This replaces
        ;; the pipe ('|') with a line break. 
        if InStr(k, "|")
        {
          jp := StrReplace(jp, "7c", "0a")
          en := StrReplace(en, "7c", "0a")
        }

        ;; Add null term to end of jp string
        jp .= 00

        ;; Add null terms until the length of the en string
        ;; matches the jp string.
        Loop
        {
          en .= 00
          new_len := StrLen(en)
        }
        Until ((jp_len - new_len) == 0)
      }
      memWrite(jp, en, jp_raw, en_raw, startAddr, endAddr)
    }
  }
}