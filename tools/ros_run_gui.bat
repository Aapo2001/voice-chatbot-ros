@echo off
REM ─────────────────────────────────────────────────────────────────
REM  ros_run_gui.bat — Launch the ROS 2 voice chatbot GUI
REM
REM  Uses a Python wrapper (run_ros_gui.py) that fixes PySide6 DLL
REM  loading before any Qt imports, avoiding conflicts with conda
REM  environment Qt libraries.
REM ─────────────────────────────────────────────────────────────────
setlocal

if not exist "install\setup.bat" (
    echo ERROR: install\setup.bat not found. Run `pixi run build` first.
    exit /b 1
)

call "install\setup.bat"
if errorlevel 1 (
    echo ERROR: Failed to activate the local ROS workspace.
    exit /b 1
)

python "%~dp0run_ros_gui.py"
