@echo off
title SnipasteOCR Build Tool

:menu
cls
echo ================================
echo      SnipasteOCR Builder
echo ================================
echo 1. Debug Build (with console)
echo 2. Release Build (no console)
echo 3. Clean Build Files
echo 4. Exit
echo ================================
echo.

set /p choice=Select an option (1-4): 
set choice=%choice:~0,1%

if "%choice%"=="1" goto debug
if "%choice%"=="2" goto release
if "%choice%"=="3" goto clean
if "%choice%"=="4" goto end
goto menu

:clean
echo Cleaning build files...
if exist "build" rd /s /q build
if exist "dist" rd /s /q dist
if exist "*.spec" del /f /q *.spec
echo Done!
pause
goto menu

:debug
call :clean_build
echo Building Debug version...
uv run pyinstaller -c main.py ^
    --collect-all fastdeploy ^
    --name=SnipasteOCR ^
    --icon=assets/icon.ico ^
    --add-data=models;models ^
    --add-data=assets;assets ^
    --add-data=config.yml;. ^
    --hidden-import=pyqt6 ^
    --hidden-import=PyQt6.QtWidgets ^
    --hidden-import=PyQt6.QtGui ^
    --hidden-import=PyQt6.QtCore ^
    --hidden-import=PyQt6.sip ^
    --clean ^
    --noconfirm

if errorlevel 1 (
    echo Build failed! Check the error message.
    pause
    goto menu
)
goto finish

:release
call :clean_build
echo Building Release version...
uv run pyinstaller -w main.py ^
    --collect-all fastdeploy ^
    --name=SnipasteOCR ^
    --icon=assets/icon.ico ^
    --add-data=models;models ^
    --add-data=assets;assets ^
    --add-data=config.yml;. ^
    --hidden-import=pyqt6 ^
    --hidden-import=PyQt6.QtWidgets ^
    --hidden-import=PyQt6.QtGui ^
    --hidden-import=PyQt6.QtCore ^
    --hidden-import=PyQt6.sip ^
    --clean ^
    --noconfirm

if errorlevel 1 (
    echo Build failed! Check the error message.
    pause
    goto menu
)
goto finish

:clean_build
echo Cleaning old build files...
if exist "build" rd /s /q build
if exist "dist" rd /s /q dist
if exist "*.spec" del /f /q *.spec
goto :eof

:finish
echo. 
echo Build completed!
echo Output directory: dist/SnipasteOCR/
echo Executable: dist/SnipasteOCR/SnipasteOCR.exe
pause
goto menu

:end
exit