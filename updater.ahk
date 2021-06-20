#Persistent
#NoEnv
#SingleInstance force
#Include <JSON>

/*
****************************************************
Used to auto update dqxclarity to the latest version
****************************************************
*/

;=== Display GUI to user showing the update is happening =======================
Gui, -SysMenu +AlwaysOnTop +E0x08000000
Gui, Add, Progress, w500 h15 c0096FF Background0a2351 vProgress, 0
Gui, Font, s12
Gui, Add, Edit, vNotes w500 r10 +ReadOnly -WantCtrlA -WantReturn, Updating..
Gui, Add, Button, w60 +x225 Default +Disabled, OK
Gui, Show, Autosize
;===============================================================================

;; Make sure /tmp is clean by deleting + re-creating, then move updater into /tmp.
FileRemoveDir, %A_ScriptDir%\tmp, 1
Sleep 100
FileCreateDir, %A_ScriptDir%\tmp
Sleep 100
FileDelete, %A_ScriptDir%\dqxclarity.zip  ;; Delete the old file if it exists
Sleep 100
FileMove, %A_ScriptDir%\updater.exe, %A_ScriptDir%\tmp\updater.exe

;; Download latest version
url := "https://github.com/jmctune/dqxclarity/releases/latest/download/dqxclarity.zip"
downloadFile(url)
GuiControl,, Progress, 25

;; Grab release notes + new version number
oWhr := ComObjCreate("WinHttp.WinHttpRequest.5.1")
url := "https://api.github.com/repos/jmctune/dqxclarity/releases/latest"
oWhr.Open("GET", url, 0)
oWhr.Send()
oWhr.WaitForResponse()
jsonResponse := JSON.Load(oWhr.ResponseText)
releaseVersion := (jsonResponse.tag_name)
releaseVersion := SubStr(releaseVersion, 2)
releaseNotes := (jsonResponse.body)
releaseNotes := RegExReplace(releaseNotes, "\r\n", "`n")
GuiControl,, Progress, 50

;; Unzip files that were downloaded into same directory, overwriting anything
unzipName := A_ScriptDir "\dqxclarity.zip"
unzipLoc := A_ScriptDir
Unz(unzipName, unzipLoc)
GuiControl,, Progress, 75

;; Get current version locally from version file
FileRead, currentVersion, version

;; Compare local version with remote. If same, update was successful.
if (releaseVersion = currentVersion)
{
  GuiControl,, Progress, 100
  message := "UPDATE SUCCESSFUL!`n`dqxclarity Version: " . releaseVersion . "`n`nRelease Notes:`n`n" . releaseNotes
  GuiControl,, Notes, % message
  FileDelete, %A_ScriptDir%\dqxclarity.zip  ;; Delete the old file
  GuiControl, Enable, OK
  Return

ButtonOK:
  Run dqxclarity.exe
  ExitApp

}
;; If versions are different, update failed. Make user aware and send them to github to download.
else
{
  GuiControl,, Progress, 100
  FileMove, %A_ScriptDir%\tmp\updater.exe, %A_ScriptDir%\updater.exe  ;; If failed, put updater back
  Sleep 100
  FileRemoveDir, %A_ScriptDir%\tmp, 1  ;; Remove /tmp folder
  message := "UPDATE FAILED! Version mismatch. Please update dqxclarity manually."
  GuiControl,, Notes, % message
  FileDelete, %A_ScriptDir%\dqxclarity.zip  ;; Delete the old file if it exists
  Run, https://github.com/jmctune/dqxclarity/releases/latest
  Sleep 5000
  ExitApp
}

;=== Functions ==========================================================
downloadFile(url, dir := "", fileName := "dqxclarity.zip") 
{
  whr := ComObjCreate("WinHttp.WinHttpRequest.5.1")
  whr.Open("GET", url, true)
  whr.Send()
  whr.WaitForResponse()

  body := whr.ResponseBody
  data := NumGet(ComObjValue(body) + 8 + A_PtrSize, "UInt")
  size := body.MaxIndex() + 1

  if !InStr(FileExist(dir), "D")
    FileCreateDir % dir

  SplitPath url, urlFileName
  f := FileOpen(dir (fileName ? fileName : urlFileName), "w")
  f.RawWrite(data + 0, size)
  f.Close()
}

Unz(sZip, sUnz)
{
  FileCreateDir, %sUnz%
    psh  := ComObjCreate("Shell.Application")
    psh.Namespace( sUnz ).CopyHere( psh.Namespace( sZip ).items, 4|16 )
}