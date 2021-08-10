SHELL=cmd

build:
	python setup.py

test:
	python main.py -c

dump:
	python main.py -d

clean:
	rd /s/q "build\" 2>null
	rd /s/q "dist\" 2>null
	rd /s/q "game_file_dumps\" 2>null
	del /F "dqxclarity.spec" 2>null
	del /F "null"