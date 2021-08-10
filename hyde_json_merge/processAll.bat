@echo off
for %%f in (hyde_json_merge/src/*.json) do json-conv.exe -s src\%%f -d dst\%%f -o out\%%f