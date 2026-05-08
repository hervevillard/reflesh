@echo off
title ArtSegment — SAM3 Windows patch
color 0A

echo.
echo  ================================================
echo   ArtSegment  ^|  SAM3 Windows Patch
echo  ================================================
echo.
echo  Run this after every SAM3 reinstall to restore
echo  Windows compatibility fixes.
echo.

if not exist venv\Scripts\python.exe (
    echo  [ERROR] No virtual environment found.
    echo  Run launch.bat first to create it.
    echo.
    pause
    exit /b 1
)

venv\Scripts\python patch_sam3.py
if errorlevel 1 (
    echo.
    echo  [ERROR] Patch failed. See error above.
    pause
    exit /b 1
)

echo.
pause
