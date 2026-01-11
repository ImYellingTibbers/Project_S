@echo off
REM ==========================================
REM Project S - Global YouTube Upload Scheduler
REM ==========================================

SET ROOT=E:\Project_S_v1.0

REM ---- CHANNEL DEFINITIONS ----
REM Format:
REM   CHANNEL_NAME|RELATIVE_PATH_TO_UPLOAD_NEXT

REM ==========================================
REM Residual Fear Uploads
REM ==========================================

SET CHANNEL_1_NAME="Project S Residual Fear 10AM"
SET CHANNEL_1_SCRIPT=%ROOT%\residual_fear\upload_next.bat

SET CHANNEL_2_NAME="Project S Residual Fear 2PM"
SET CHANNEL_2_SCRIPT=%ROOT%\residual_fear\upload_next.bat

SET CHANNEL_3_NAME="Project S Residual Fear 6PM"
SET CHANNEL_3_SCRIPT=%ROOT%\residual_fear\upload_next.bat

REM ==========================================
REM Channel 2 Uploads
REM ==========================================

echo.
echo === Clearing existing Project S upload tasks ===

schtasks /delete /tn %CHANNEL_1_NAME% /f >nul 2>&1
schtasks /delete /tn %CHANNEL_2_NAME% /f >nul 2>&1
schtasks /delete /tn %CHANNEL_3_NAME% /f >nul 2>&1

echo Tasks cleared.

@REM echo.
@REM echo === Creating upload tasks ===

@REM schtasks /create ^
@REM   /tn %CHANNEL_1_NAME% ^
@REM   /tr "%CHANNEL_1_SCRIPT%" ^
@REM   /sc daily ^
@REM   /st 10:00 ^
@REM   /rl highest ^
@REM   /f

@REM schtasks /create ^
@REM   /tn %CHANNEL_2_NAME% ^
@REM   /tr "%CHANNEL_2_SCRIPT%" ^
@REM   /sc daily ^
@REM   /st 14:00 ^
@REM   /rl highest ^
@REM   /f

@REM schtasks /create ^
@REM   /tn %CHANNEL_3_NAME% ^
@REM   /tr "%CHANNEL_3_SCRIPT%" ^
@REM   /sc daily ^
@REM   /st 18:00 ^
@REM   /rl highest ^
@REM   /f

@REM echo.
@REM echo === All Project S upload tasks installed ===
pause
