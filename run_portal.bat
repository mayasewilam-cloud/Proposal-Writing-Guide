@echo off
title BioWriter Studio - BT_301 Socratic Writing & Research Portal
color 0A

echo ==============================================================================
echo                 BioWriter Studio: Socratic Proposal Portal                   
echo               Course: BT_301 (Introduction to Biotechnology)                 
echo ==============================================================================
echo.
echo [1/2] Launching BioWriter Studio Server...
echo [2/2] Opening browser at http://127.0.0.1:5000 ...
echo.
echo Press Ctrl+C in this terminal window to stop the server.
echo.

start "" "http://127.0.0.1:5000"
python app.py
pause
