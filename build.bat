@echo off
echo Stage 1: Cleaning environment...
if exist "dist" rd /s /q "dist"
if exist "build" rd /s /q "build"

echo Stage 2: Downloading required standalone tools...
echo Downloading latest yt-dlp...
powershell -Command "[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.SecurityProtocolType]::Tls12; $ProgressPreference = 'SilentlyContinue'; Invoke-WebRequest -Uri 'https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe' -OutFile 'yt-dlp.exe' -UseBasicParsing"

if not exist "ffmpeg.exe" (
    echo Downloading ffmpeg...
    powershell -Command "[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.SecurityProtocolType]::Tls12; $ProgressPreference = 'SilentlyContinue'; Invoke-WebRequest -Uri 'https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip' -OutFile 'ffmpeg.zip' -UseBasicParsing; Expand-Archive -Path 'ffmpeg.zip' -DestinationPath '.';"
    move ffmpeg-master-latest-win64-gpl\bin\ffmpeg.exe .
    move ffmpeg-master-latest-win64-gpl\bin\ffprobe.exe .
    rd /s /q ffmpeg-master-latest-win64-gpl
    del ffmpeg.zip
)

echo Stage 3: Installing Python build dependencies...
pip install --upgrade -r requirements.txt

echo Stage 4: Building Independent EXE...
:: --uac-admin is REQUIRED for the symbolic link (sync) feature to work
python -m PyInstaller --noconfirm --windowed --onefile  --uac-admin ^
    --exclude-module tzdata ^
    --add-binary "yt-dlp.exe;." ^
    --add-binary "ffmpeg.exe;." ^
    --add-binary "ffprobe.exe;." ^
    --name "MusicSyncManager" ^
    --icon "icon.ico" ^
    "main.py"

echo SUCCESS! Check the 'dist' folder for your independent MusicSyncManager.exe
:: Only pause if the script was double-clicked manually, skip if run by GitHub
if "%GITHUB_ACTIONS%"=="" pause