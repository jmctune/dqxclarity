#Persistent
#NoEnv
#SingleInstance, Force

/*
*************************************************
Pulls down the latest JSON files from main
*************************************************
*/

;=== Display GUI to user showing the update is happening =======================
Gui, -SysMenu +AlwaysOnTop +E0x08000000
Gui, Add, Progress, w500 h15 c0096FF Background0a2351 vProgress, 0
Gui, Font, s12
Gui, Add, Edit, vNotes w500 r10 +ReadOnly -WantCtrlA -WantReturn, Downloading..
Gui, Show, Autosize
;===============================================================================

;; Remove old JSON files and create tmp dir
FileRemoveDir, %A_ScriptDir%\json, 1
Sleep 100
FileCreateDir, %A_ScriptDir%\json\_lang\en
Sleep 100
FileRemoveDir, %A_ScriptDir%\tmp
Sleep 100
FileCreateDir, %A_ScriptDir%\tmp

;; Download latest version
url := "https://github.com/jmctune/dqxclarity/archive/refs/heads/weblate.zip"
downloadFile(url)
GuiControl,, Progress, 25

;; Move file and unzip
unzipName := A_ScriptDir "\weblate.zip"
unzipLoc := A_ScriptDir
Unz(unzipName, unzipLoc)
GuiControl,, Progress, 50

;; Move files from extracted json folder into main directory
FileMove, %A_ScriptDir%\dqxclarity-weblate\json\_lang\en\*.json, %A_ScriptDir%\json\_lang\en
GuiControl,, Progress, 75
Sleep 100

;; Delete tmp dirs
FileRemoveDir, %A_ScriptDir%\dqxclarity-weblate, 1
FileDelete, %A_ScriptDir%\main.zip
FileDelete, %A_ScriptDir%\weblate.zip
GuiControl,, Progress, 100

;; Finish up
if FileExist("json\_lang\en\*.json")
{
  GuiControl,, Notes, JSON files updated.
  Sleep 2000
  Run dqxclarity.exe
  ExitApp
}
else
{
  GuiControl,, Notes, JSON files were not updated. Please redownload the JSON files manually as they currently do not exist in your directory.
  Sleep 5000
  ExitApp
}

;=== Functions ==========================================================
downloadFile(url, dir := "", fileName := "weblate.zip") 
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
  psh  := ComObjCreate("Shell.Application")
  psh.Namespace( sUnz ).CopyHere( psh.Namespace( sZip ).items, 4|16 )
}
