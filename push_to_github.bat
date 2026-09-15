@echo off
cd /d "%~dp0"
echo ======================================================
echo Pushing latest Vercel fixes to GitHub...
echo ======================================================
git push origin main
if %ERRORLEVEL% EQU 0 (
    echo.
    echo ======================================================
    echo [SUCCESS] Code pushed to GitHub successfully!
    echo Vercel is now building the fixed version.
    echo ======================================================
) else (
    echo.
    echo ======================================================
    echo [ERROR] Push failed. If prompted, please sign in.
    echo ======================================================
)
pause
