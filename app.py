from flask import Flask, request, jsonify, send_file, render_template, redirect, url_for, flash
import yt_dlp
import os
import shutil
import subprocess
import threading
import time
from waitress import serve
import logging
import traceback
import secrets

# Configure logging
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'default_secret_key')

# Set the path to the FFmpeg executable
FFMPEG_PATH = os.path.join(os.getcwd(), "ffmpeg", "ffmpeg.exe")
VIDEO_DIR = os.getenv('VIDEO_DIR', os.path.join(os.getcwd(), "ALL_VIDEOS"))

# Path to store uploaded cookies
COOKIES_PATH = os.getenv('COOKIES_PATH', os.path.join(os.getcwd(), "cookies.txt"))

logging.debug(f"COOKIES_PATH: {COOKIES_PATH}")  # Log the cookies path

def find_ffmpeg():
    logging.debug(f"FFMPEG_PATH: {FFMPEG_PATH}")  # Log the environment variable
    if os.path.isfile(FFMPEG_PATH):
        return FFMPEG_PATH
    else:
        logging.error(f"FFmpeg not found at specified path: {FFMPEG_PATH}")
        return None

def ensure_video_dir():
    if not os.path.exists(VIDEO_DIR):
        os.makedirs(VIDEO_DIR)

def delete_old_videos():
    while True:
        time.sleep(1800)  # Wait for 30 minutes
        for filename in os.listdir(VIDEO_DIR):
            file_path = os.path.join(VIDEO_DIR, filename)
            try:
                if os.path.isfile(file_path):
                    os.remove(file_path)
                    print(f"Deleted {file_path}")
            except Exception as e:
                print(f"Error deleting file {file_path}: {e}")

def list_formats(url):
    try:
        ffmpeg_path = find_ffmpeg()
        if not ffmpeg_path:
            return "FFmpeg not found. Cannot proceed."

        opts = {
            'ffmpeg_location': ffmpeg_path,
            'listformats': True
        }
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            formats = [
                {
                    "id": fmt['format_id'],
                    "resolution": f"{fmt.get('height', 'Unknown')}p" if 'height' in fmt else "Audio Only",
                    "fps": fmt.get('fps', "N/A"),
                    "filesize": fmt.get('filesize', "Unknown"),
                    "ext": fmt['ext'],
                    "type": "both" if fmt.get('vcodec') != 'none' and fmt.get('acodec') != 'none' else "video" if fmt.get('vcodec') != 'none' else "audio"
                }
                for fmt in info.get('formats', [])
            ]
            return formats
    except yt_dlp.utils.DownloadError as e:
        return f"Download error: {e}"
    except Exception as e:
        return f"Unexpected error: {e}"

def download_video(url, format_id, output_filename, trim_start, trim_end):
    try:
        ensure_video_dir()
        ffmpeg_path = find_ffmpeg()
        if not ffmpeg_path:
            return "FFmpeg not found. Cannot proceed."

        video_output = os.path.join(VIDEO_DIR, f'{output_filename}_video.mp4')
        audio_output = os.path.join(VIDEO_DIR, f'{output_filename}_audio.m4a')
        final_output = os.path.join(VIDEO_DIR, f'{output_filename}.mp4')

        # Download video and audio separately
        video_opts = {
            'ffmpeg_location': ffmpeg_path,
            'format': f'{format_id}',  # Download only the video
            'outtmpl': video_output,
            'cookiefile': COOKIES_PATH,  # Use the uploaded cookies
            'extractor_args': {
                'youtube': {
                    'visitor_data': 'YOUR_VISITOR_DATA_HERE'  # Replace with actual visitor data if needed
                }
            }
        }
        audio_opts = {
            'ffmpeg_location': ffmpeg_path,
            'format': 'bestaudio',  # Download only the audio
            'outtmpl': audio_output,
            'cookiefile': COOKIES_PATH,  # Use the uploaded cookies
            'extractor_args': {
                'youtube': {
                    'visitor_data': 'YOUR_VISITOR_DATA_HERE'  # Replace with actual visitor data if needed
                }
            }
        }

        with yt_dlp.YoutubeDL(video_opts) as ydl:
            ydl.download([url])

        with yt_dlp.YoutubeDL(audio_opts) as ydl:
            ydl.download([url])

        # Merge video and audio
        merge_command = [
            ffmpeg_path, '-i', video_output, '-i', audio_output,
            '-c:v', 'copy', '-c:a', 'aac', '-strict', 'experimental'
        ]

        # Add trimming options if specified
        if trim_start and trim_end:
            merge_command.extend(['-ss', trim_start, '-to', trim_end])

        merge_command.append(final_output)
        subprocess.run(merge_command, check=True)

        # Clean up intermediate files
        os.remove(video_output)
        os.remove(audio_output)

        return final_output
    except yt_dlp.utils.DownloadError as e:
        return f"Download error: {e}"
    except Exception as e:
        return f"Unexpected error: {e}"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/.well-known/health')
def health_check():
    return jsonify({"status": "healthy"}), 200

@app.route('/formats', methods=['POST'])
def get_formats():
    data = request.json
    url = data.get('url')
    formats = list_formats(url)
    return jsonify(formats)

@app.route('/download', methods=['POST'])
def download():
    data = request.json
    url = data.get('url')
    format_id = data.get('format_id')
    output_filename = data.get('output_filename')
    trim_start = data.get('trim_start')
    trim_end = data.get('trim_end')

    result = download_video(url, format_id, output_filename, trim_start, trim_end)
    if os.path.exists(result):
        return send_file(result, as_attachment=True)
    else:
        return jsonify({"error": result}), 400

@app.route('/upload-cookies', methods=['POST'])
def upload_cookies():
    logging.debug("Upload cookies endpoint hit.")
    
    if 'cookies' not in request.files:
        flash("No file part", "error")
        logging.error("No file part in the request.")
        return redirect(url_for('index'))
    
    file = request.files['cookies']
    logging.debug(f"File received: {file.filename}")
    
    if file.filename == '':
        flash("No selected file", "error")
        logging.error("No selected file.")
        return redirect(url_for('index'))
    
    if file:
        try:
            file.save(COOKIES_PATH)
            flash("Cookies uploaded successfully!", "success")  # Flash success message
            logging.info(f"Cookies uploaded and saved to {COOKIES_PATH}.")
        except Exception as e:
            flash(f"Error saving cookies: {str(e)}", "error")  # Flash error message
            logging.error(f"Error saving cookies: {str(e)}")
        return redirect(url_for('index'))  # Redirect to the index page after upload

def create_default_cookies():
    # Example content for cookies.txt
    default_cookies = """# Netscape HTTP Cookie File
# http://curl.haxx.se/rfc/cookie_spec.html
# This file was generated by a script.
# Edit at your own risk.

.example.com    TRUE    /    FALSE    2147483647    session_id    your_session_id_here
"""
    with open(COOKIES_PATH, 'w') as f:
        f.write(default_cookies)

@app.route('/test-upload', methods=['GET', 'POST'])
def test_upload():
    if request.method == 'POST':
        file = request.files['testfile']
        if file:
            file.save(os.path.join(os.getcwd(), "testfile.txt"))
            return "File uploaded successfully!"
    return '''
    <form method="post" enctype="multipart/form-data">
        <input type="file" name="testfile">
        <input type="submit">
    </form>
    '''

# Error handler to log exceptions
@app.errorhandler(Exception)
def handle_exception(e):
    app.logger.error(f"Error occurred: {e}")
    app.logger.error(traceback.format_exc())  # Log the full traceback
    return "Internal Server Error", 500

if __name__ == '__main__':
    # Create cookies.txt if it doesn't exist
    if not os.path.isfile(COOKIES_PATH):
        create_default_cookies()
    
    threading.Thread(target=delete_old_videos, daemon=True).start()
    print("Starting server on http://localhost:8080")  # Log the URL
    serve(app, host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))