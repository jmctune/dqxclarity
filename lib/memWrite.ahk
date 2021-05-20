memWrite(jp, en, jp_raw, en_raw, loopCount, menu_start_addr := 0x43000000, menu_end_addr := 0x49900000)
{
  menuAOB := dqx.hexStringToPattern(jp)
  menuAddress := dqx.processPatternScan(menu_start_addr,menu_end_addr, menuAOB*)

  if (menuAddress == 0)
  {
    FileAppend, Not Found: JP: %jp_raw%  EN: %en_raw%`n,problem.txt
  }
  else
  {
    FileAppend, %menuAddress%`n, address.txt

    dqx.writeBytes(menuAddress, en)

    if (loopCount > 1)
    {
      loopCount := (loopCount - 1)
      loop, %loopCount%
      {
        menuAddress := dqx.processPatternScan(menuAddress + 1, menu_end_addr, menuAOB*)

        if (menuAddress == 0)
        {
          FileAppend, Not Found: JP: %jp_raw%  EN: %en_raw%`n ,problem.txt
          break
        }

        dqx.writeBytes(menuAddress, en)
        FileAppend, %menuAddress%`n, address.txt
      }
    }
  }
}