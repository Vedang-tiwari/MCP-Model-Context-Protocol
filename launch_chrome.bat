@echo off
echo ========================================================
echo Launching Official Google Chrome for MCP Application Agent
echo Remote Debugging Port: 9222
echo ========================================================
start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --no-first-run
echo Google Chrome is running!
echo All job applications will now open as new tabs in this same browser.
