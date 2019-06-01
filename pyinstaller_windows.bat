pyinstaller -y -F -w ^
    -i "bakalaris.ico" ^
    -n Bakalaris "main.py" ^
    --distpath "release"
rd /s /q "build"
del "Bakalaris.spec"