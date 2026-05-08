@echo off
title ArtSegment
color 0A

echo.
echo  ================================================
echo   ArtSegment  ^|  AI Image Segmentation for Artists
echo  ================================================
echo.

:: Create virtual environment on first run
if not exist "venv\Scripts\activate.bat" (
    echo  [SETUP] Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo  [ERROR] Failed to create venv. Is Python installed?
        pause
        exit /b 1
    )

    call venv\Scripts\activate.bat

    echo  [SETUP] Installing dependencies ^(this takes a few minutes on first run^)...
    pip install --upgrade pip -q
    pip install -r requirements.txt -q
    if errorlevel 1 (
        echo  [ERROR] Failed to install dependencies.
        pause
        exit /b 1
    )

    echo  [SETUP] Installing SAM2 from Meta...
    pip install git+https://github.com/facebookresearch/sam2.git -q
    if errorlevel 1 (
        echo  [ERROR] Failed to install SAM2. Check internet connection.
        pause
        exit /b 1
    )

    echo  [SETUP] Setup complete!
    echo.
) else (
    call venv\Scripts\activate.bat
)

echo  Launching ArtSegment...
echo  (SAM2 model will be downloaded automatically on first analyze)
echo.
python main.py

if errorlevel 1 (
    echo.
    echo  [ERROR] ArtSegment exited with an error.
    pause
)
