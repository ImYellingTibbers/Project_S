@echo off
REM Upload one queued YouTube video for Project S

SET PROJECT_ROOT=E:\Project_S_v1.0\residual_fear
SET PYTHON_EXE=C:\Users\jcpix\AppData\Local\Programs\Python\Python311\python.exe

cd /d %PROJECT_ROOT%

%PYTHON_EXE% src\uploader\queued_youtube_uploader.py >> upload.log 2>&1
