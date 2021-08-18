SHELL=cmd

build:
	python setup.py

release:
	make clean
	make build
	move dist\dqxclarity.exe .
	"C:\Program Files\7-Zip\7z.exe" a -tzip dqxclarity.zip -r json/_lang/en json/_lang/ja dqxclarity.exe hex_dict.csv
	python calculate_sha.py

lint:
	pylint --rcfile=.pylintrc setup.py
	pylint --rcfile=.pylintrc main.py
	pylint --rcfile=.pylintrc clarity.py

clean:
	if exist "build\" rd /s/q "build\"
	if exist "dist\" rd /s/q "dist\"
	if exist "game_file_dumps\" rd /s/q "game_file_dumps\"
	if exist "dqxclarity.spec" del /F "dqxclarity.spec"
	if exist "dqxclarity.zip" del /F "dqxclarity.zip"
	if exist "dqxclarity.exe" del /F "dqxclarity.exe"