set PYTHONOPTIMIZE=1 && pyinstaller -y -F ^
                        -i "bakalaris.ico" ^
                        -n Bakalaris "main.py" ^
                        --distpath "release"
rd /s /q "build"
del "Bakalaris.spec"