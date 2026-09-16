@echo off
cd /d "%~dp0\..\.."
python demo-ui/spatial-poc/integrated_server.py --generator disconnected --port 8769
pause
