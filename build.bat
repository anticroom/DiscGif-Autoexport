@echo off
echo Installing dependencies...
pip install -r requirements.txt
pip install pyinstaller

echo.
echo Building executable...
pyinstaller --onefile --noconsole --name "DiscordGifExtractor" main.py

echo.
echo Build complete. Check the 'dist' folder for your executable.
pause