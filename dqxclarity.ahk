#SingleInstance, Force
#Include <classMemory>
#Include <convertHex>
#Include <JSON>
#Include <hashCheck>

SetBatchLines, -1
FileEncoding UTF-8

Process, Exist, DQXGame.exe
if !ErrorLevel
{
  MsgBox Dragon Quest X must be running for dqxclarity to run.
  ExitApp
}

;=== Auto update ============================================================
;; Get latest version number from Github
oWhr := ComObjCreate("WinHttp.WinHttpRequest.5.1")
url := "https://api.github.com/repos/jmctune/dqxclarity/releases/latest"
oWhr.Open("GET", url, 0)
oWhr.Send()
oWhr.WaitForResponse()
jsonResponse := JSON.Load(oWhr.ResponseText)
latestVersion := (jsonResponse.tag_name)
latestVersion := SubStr(latestVersion, 2)

;; Get current version locally from version file
FileRead, currentVersion, version

;; If the versions differ, run updater
if (latestVersion != currentVersion)
{
  if (latestVersion = "" || currentVersion = "")
  {
    MsgBox Unable to determine latest version. Continuing without updating.
  }
  else
  {
    Run updater.exe
    ExitApp
  }
}
else
{
tmpLoc := A_ScriptDir "\tmp"
if FileExist(tmpLoc)
  FileRemoveDir, %A_ScriptDir%\tmp, 1
  sleep 50
}

;; === UI ========================================================================
;; Create GUI
Gui, 1:Default
Gui, Add, Tab3,, General|Update|About
Gui, Font, s10, Segoe UI
Gui, Add, Text,, dqxclarity
Gui, Add, Text, y+1, Finally, a somewhat localized DQX. 
Gui, Add, Picture, vImage w107 h-1 +Center, imgs/rosie.ico
Gui, Add, Button, gRun +Default w100, Go

;; Update tab
Gui, Tab, Update
Gui, Add, Button, gUpdateJSON, Get Weblate Files
Gui, Add, Link,, Get the latest translations from the`nweblate branch. This can cause Clarity`nto fail to process files if bad`ntranslations were checked in, but`ngives you the most up to date translations.`n`nIf you find a broken translation, please`n<a href="https://weblate.ethene.wiki/">volunteer to fix it!</a>

;; About tab
Gui, Tab, About
Gui, Add, Link,, <a href="https://discord.gg/UFaUHBxKMY">Discord</a>
Gui, Add, Link,, <a href="https://github.com/jmctune/dqxclarity">Get the Source</a>
Gui, Add, Link,, Like what I'm doing? <a href="https://ko-fi.com/serany">Donate :P</a>
Gui, Add, Text,, Catch me on Discord: mebo#1337
Gui, Add, Link,, Core app made by Serany <3 `n`nTranslations done by several members`nof the DQX community.`n<a href="https://github.com/jmctune/dqxclarity/graphs/contributors">Check them out!</a> 

Gui, Show, Autosize
Return

UpdateJSON:
  Run, %A_ScriptDir%\json_latest.exe
  ExitApp
  Return

Run:
  Gui, Submit, Hide

;; Open Progress UI
Gui, 2:Default
Gui, Font, s12
Gui, +AlwaysOnTop +E0x08000000
Gui, Add, Edit, vProgress w500 r10 +ReadOnly -WantCtrlA -WantReturn,
Gui, Show, Autosize
;; === UI ========================================================================

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

;; === SCRIPT START ==============================================================
;; get AOBs for start/end
startAOB := dqx.hexStringToPattern("49 4E 44 58 10 00 00") ;; INDX block start
textAOB := dqx.hexStringToPattern("54 45 58 54 10 00 00") ;; TEXT block start
start_addr := 0

;; Start timer
GuiControl,, Progress, CPU usage will spike while this is running.`n`nIf new translations were pulled from weblate, this will take longer.
startTime := A_TickCount

Loop
{
  ;; iterate through each file loaded into mem
  start_addr := dqx.processPatternScan(start_addr,, startAOB*)  ;; find each unique block

  ;; if we can't find any more matches, we're done
  if start_addr = 0
    break

  ;; we found a match, so keep going
  hex_start := dqx.readRaw(start_addr, hexbuf, 64)
  hex_start := bufferToHex(hexbuf, 64)  ;; get hex of buffer, which we use for the lookup against the hex_dict
  start_addr := dqx.processPatternScan(start_addr,, textAOB*)  ;; jump to the start of the block

  ;; remove beginning TEXT[] garbage and get towards end
  start_addr := start_addr + 14

  ;; loop from where we ended up until we stop getting null terms.
  ;; this is the true beginning of the address we want to write to.
  loop
  { 
    start_addr := start_addr + 1
    result := dqx.readRaw(start_addr, buffer, 1)
    result := bufferToHex(buffer, 1)
  } until (result != 00)

  ;; for our first write, we want to be one address behind because we will
  ;; be including a null term at the beginning of the string, so go back one.
  start_addr := start_addr - 1

  ;; parse master csv to figure out what the file is
  fileName := ""
  Loop, Read, hex/hex_dict.csv
  {
    Loop, Parse, A_LoopReadLine, CSV
    {
      if (A_LoopField = hex_start)
      {
        split := StrSplit(A_LoopReadLine, ",")
        fileName := split[1]
        break
      }
    }
  }

  ;; if the entry doesn't exist in the hex_dict, skip to the
  ;; next address as we don't know what to write
  if (fileName = "")
    continue

  ;; compare checksum of json file with saved checksum. if different,
  ;; tell run_json to rebuild it
  checksum := ""
  jsonChecksum := hashCheck(fileName)
  SplitPath, fileName,,,, name_no_ext
  FileRead, checksum, hex/checksums/%name_no_ext%.md5
  if (checksum = jsonChecksum)
    rebuild := "false"
  else
    rebuild := "true"

  Run, run_json.exe %fileName% %start_addr% %rebuild%
}

numberOfRunningProcesses := 1
;; Let user know how many files are left to process
while (numberOfRunningProcesses != 0)
{
  numberOfRunningProcesses = 0
  for process in ComObjGet("winmgmts:").ExecQuery("Select * from Win32_Process")
  {
    if process.Name = "run_json.exe"
      numberOfRunningProcesses++
  }
  GuiControl,, Progress, Files remaining: %numberOfRunningProcesses%
  sleep 500
}

elapsedTime := A_TickCount - startTime
GuiControl,, Progress, Done.`n`nElapsed time: %elapsedTime%ms
Sleep 750

ExitApp

GuiEscape:
GuiClose:
  ExitApp
