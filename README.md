# yt-downloader

## Requirements
- Python 3.x
- Flask
- yt-dlp
- requests
- ffmpeg-python

## Setup Instructions
1. Clone the repository.
2. Ensure you have the `ffmpeg` directory in the project root containing `ffmpeg.exe`.
3. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```
4. Run the application:
   ```bash
   python app.py
   ```

## Environment Variables
- `FFMPEG_PATH`: Path to the FFmpeg executable (default is set to `./ffmpeg/ffmpeg.exe`).
- `VIDEO_DIR`: Directory to store downloaded videos (default is `./ALL_VIDEOS`).