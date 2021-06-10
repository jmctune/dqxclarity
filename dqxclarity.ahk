#SingleInstance, Off
#Include <classMemory>
#Include <convertHex>
#Include <memWrite>
#Include <JSON>
#Include <JSON_coco>

SetBatchLines, -1

Process, Exist, DQXGame.exe
if !ErrorLevel
{
  MsgBox Dragon Quest X must be running for dqxclarity to work.
  ExitApp
}

;=== Auto update ============================================================
;; Get latest version number from Github
oWhr := ComObjCreate("WinHttp.WinHttpRequest.5.1")
url := "https://api.github.com/repos/jmctune/dqxclarity/releases/latest"
oWhr.Open("GET", url, 0)
oWhr.Send()
oWhr.WaitForResponse()
jsonResponse := JSON_coco.Load(oWhr.ResponseText)
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

;; Create GUI
Gui, 1:Default
Gui, Add, Tab3,, General|Update|About
Gui, Font, s10, Segoe UI
Gui, Add, Text,, Number of files to process at once`n(Higher number uses more CPU)
Gui, Add, Edit
Gui, Add, UpDown, vParallelProcessing Range1-50, 15
Gui, Add, Button, gRun, Run

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

UpdateApp:
  Run, %A_ScriptDir%\updater.exe
  ExitApp
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
Gui, Add, Edit, vNotes w500 r10 +ReadOnly -WantCtrlA -WantReturn,
Gui, Show, Autosize

;; Start timer
startTime := A_TickCount

;; Get number of files we're going to process
numberOfFiles := 0
Loop, json\_lang\ja\*.json
  if InStr(A_LoopFileFullPath, ".dummy.json")
    continue
  else
    numberOfFiles++

;; Open a process to check if the user has already run
;; Clarity during their DQX session. If so, don't let them run it again.
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

GuiControl,, Notes, Checking if Clarity can run...
textHex := dqx.hexStringToPattern("54 45 58 54 10 00 00 00 F0 01 00 00 00 00 00 00 00 00 E3 82 A8") ;; classes_races.json
if (dqx.processPatternScan(,,textHex*) == 0)
{
  GuiControl,, Notes, You've already run Clarity during this Dragon Quest X session. Please close and re-open Dragon Quest X to rerun Clarity.
  Sleep 4000
  ExitApp
}

;; Loop through all files in json directory
numberOfRunningProcesses := 0
Loop, json\_lang\ja\*.json, F
{
  if InStr(A_LoopFileFullPath, ".dummy.json")
    continue
  else
    Loop
    {
      numberOfRunningProcesses := 0
      for process in ComObjGet("winmgmts:").ExecQuery("Select * from Win32_Process")
      {
        if process.Name = "run_json.exe"
          numberOfRunningProcesses++
      }
    }
    Until (numberOfRunningProcesses < ParallelProcessing)   ;; Limit throughput processing based on user input.

    Run, %A_ScriptDir%\run_json.exe %A_LoopFileFullPath%
    numberOfFiles := (numberOfFiles - 1)
    GuiControl,, Notes, Queued files waiting to process: %numberOfFiles%`n`nCurrent files processing: %numberOfRunningProcesses%
}

;; Let user know how many files are left to process
while (numberOfRunningProcesses != 0)
{
  numberOfRunningProcesses = 0
  for process in ComObjGet("winmgmts:").ExecQuery("Select * from Win32_Process")
  {
    if process.Name = "run_json.exe"
      numberOfRunningProcesses++
  }
  GuiControl,, Notes, Number of files left to translate: %numberOfRunningProcesses%
  sleep 500
}

elapsedTime := A_TickCount - startTime
GuiControl,, Notes, Done.`n`nElapsed time: %elapsedTime%ms
Sleep 750

ExitApp

GuiEscape:
GuiClose:
  ExitApp
