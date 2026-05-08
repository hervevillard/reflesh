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

    echo  [SETUP] Installing PyTorch with CUDA support...
    echo  ^(downloading ~2 GB CUDA wheels from download.pytorch.org — this may take a while^)
    pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128 -q
    if errorlevel 1 (
        echo  [ERROR] Failed to install PyTorch with CUDA.
        echo  Check your internet connection to download.pytorch.org and retry.
        pause
        exit /b 1
    )

    echo  [SETUP] Installing remaining dependencies...
    pip install --upgrade pip -q
    pip install -r requirements.txt -q
    if errorlevel 1 (
        echo  [ERROR] Failed to install pip dependencies.
        pause
        exit /b 1
    )

    echo  [SETUP] Installing SAM3 package...
    if exist sam3\pyproject.toml (
        pip install -e sam3 -q
    ) else (
        pip install git+https://github.com/facebookresearch/sam3.git -q
    )
    if errorlevel 1 (
        echo  [ERROR] Failed to install SAM3.
        pause
        exit /b 1
    )

    echo  [SETUP] Applying SAM3 Windows patches...
    python patch_sam3.py
    if errorlevel 1 (
        echo  [WARNING] SAM3 patch step had errors ^(see above^). The app may still work.
    )

    echo.
    echo  [AUTH] SAM3 is a gated HuggingFace model.
    echo  If you haven't already, request access at:
    echo    https://huggingface.co/facebook/sam3.1
    echo  Then authenticate:
    echo    huggingface-cli login
    echo.

    echo  [SETUP] Setup complete!
    echo.
) else (
    call venv\Scripts\activate.bat
    echo  [UPDATE] Checking for new dependencies...
    pip install -r requirements.txt -q
)

echo  Launching ArtSegment...
echo  (SAM3 weights download automatically on first Analyze — ~1 GB, cached after)
echo.

:: Suppress HuggingFace symlinks warning — Windows needs Developer Mode for symlinks;
:: the cache still works correctly without them (copies instead of symlinks).
set HF_HUB_DISABLE_SYMLINKS_WARNING=1

python main.py

if errorlevel 1 (
    echo.
    echo  [ERROR] ArtSegment exited with an error.
    pause
)
