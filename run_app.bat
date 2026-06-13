@echo off
title InsightPaper AI Launcher
cd /d "%~dp0"
echo ==========================================
echo       InsightPaper AI - Research Summarizer
echo ==========================================
echo.
echo Launching server and opening your browser...
echo Close this window to stop the application.
echo.

:: Open browser
start "" "http://localhost:8501"

:: Run Streamlit
.venv\Scripts\streamlit.exe run app.py

pause
