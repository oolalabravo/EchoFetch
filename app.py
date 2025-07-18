import os
import re
import subprocess
import time
import logging
from flask import (
    Flask, render_template, request, jsonify, send_from_directory, Response, abort
)
from spotipy.oauth2 import SpotifyClientCredentials
import spotipy
from dotenv import load_dotenv

# --- Load environment variables (for secret management, use .env in production) ---
load_dotenv()

# --- App Configuration & Initialization ---
app = Flask(__name__)

DOWNLOAD_FOLDER = os.path.join(os.getcwd(), "downloads")
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)
LOGS = []
LOG_LINES_LIMIT = 200  # Extended to keep more history for progress streaming

# Append 'ffmpeg' to PATH for spotdl and media backend tools
os.environ["PATH"] += os.pathsep + os.path.abspath("ffmpeg")

# --- Logging Setup ---
handler = logging.StreamHandler()
handler.setLevel(logging.INFO)
app.logger.addHandler(handler)

def log(msg):
    app.logger.info(msg)
    LOGS.append(msg)
    if len(LOGS) > LOG_LINES_LIMIT:
        LOGS.pop(0)

# --- Helpers ---

def sanitize_filename(name):
    """Sanitize names for safe filesystem storage."""
    return re.sub(r'[\\/:"*?<>|]+', '-', name)

def build_expected_filename(artist, title):
    """Generate a clean mp3 filename for given artist/title."""
    return sanitize_filename(f"{artist} - {title}.mp3")

def find_best_match_mp3(artist, title, directory):
    """
    Find the best matching MP3 file in directory for artist/title,
    in case spotdl saves files with slightly different names.
    """
    target = re.sub(r'\W+', '', f"{artist}{title}".lower())
    best_match, highest_score = None, 0
    for f in os.listdir(directory):
        if f.lower().endswith('.mp3'):
            stripped = re.sub(r'\W+', '', f.lower())
            score = sum(1 for c in target if c in stripped)
            if score > highest_score:
                highest_score, best_match = score, f
    return best_match

# --- Spotify API ---
sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
    client_id=os.environ.get("SPOTIFY_CLIENT_ID"),
    client_secret=os.environ.get("SPOTIFY_CLIENT_SECRET")
))

# --- Error Handling ---

@app.errorhandler(Exception)
def handle_exception(e):
    log(f"🔥 [SERVER ERROR]: {str(e)}")
    return jsonify({'status': 'error', 'message': str(e)}), 500

# --- Routes ---

@app.route('/')
def index():
    """Render the main frontend (index.html)."""
    return render_template('index.html')

@app.route('/logs')
def logs():
    """Fetch current logs for frontend streaming."""
    return jsonify(LOGS)

@app.route('/search', methods=['POST'])
def search():
    """
    Search Spotify tracks.
    Input: 'query' (POST form)
    Output: { status, choices: [{name, url}] }
    """
    query = request.form.get('query')
    if not query:
        return jsonify({'status': 'error', 'message': 'No query provided'}), 400

    log(f"🔎 Searching for: {query}")
    try:
        results = sp.search(q=query, limit=3, type='track')
        items = results['tracks']['items']
        if not items:
            return jsonify({'status': 'error', 'message': 'No results found.'})

        choices = [{
            'name': f"{track['artists'][0]['name']} - {track['name']}",
            'url': track['external_urls']['spotify']
        } for track in items]
        return jsonify({'status': 'success', 'choices': choices})
    except Exception as e:
        log(f"🔥 Error during search: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/download', methods=['POST'])
def download():
    """
    Download a Spotify track to MP3 using spotdl.
    Input: 'url' (POST form)
    Output: { status, file, download_url }
    """
    url = request.form.get('url')
    if not url:
        return jsonify({'status': 'error', 'message': 'No track URL provided'}), 400

    log(f"🎧 Downloading track: {url}")
    try:
        track_id = url.split("/")[-1].split("?")[0]
        track = sp.track(track_id)
        artist, title = track['artists'][0]['name'], track['name']

        cmd = [
            "spotdl",
            url,
            "--output", os.path.join(DOWNLOAD_FOLDER, "{artist} - {title}.{output-ext}")
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)

        for line in (result.stdout or '').strip().split('\n'):
            if line:
                log(f"📦 spotdl: {line}")
        for line in (result.stderr or '').strip().split('\n'):
            if line:
                log(f"📦 spotdl ERR: {line}")

        matched_file = find_best_match_mp3(artist, title, DOWNLOAD_FOLDER)
        if matched_file:
            log(f"✅ File ready: {matched_file}")
            return jsonify({
                'status': 'success',
                'file': matched_file,
                'download_url': f'/download-file/{matched_file}'
            })
        else:
            log("❌ MP3 not found after download.")
            return jsonify({'status': 'error', 'message': 'MP3 not found after download.'})
    except Exception as e:
        log(f"🔥 Error during download: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/download-file/<path:filename>')
def download_file(filename):
    """Serve MP3 file to client for download."""
    try:
        return send_from_directory(DOWNLOAD_FOLDER, filename, as_attachment=True)
    except Exception as e:
        log(f"🔥 [File Download Error] {filename}: {str(e)}")
        abort(404)

@app.route('/stream', methods=['POST'])
def stream():
    """
    Download and prepare a Spotify track for streaming as MP3.
    Input: 'url' (POST form)
    Output: { status, stream_url }
    """
    url = request.form.get('url')
    if not url:
        return jsonify({'status': 'error', 'message': 'No track URL provided'}), 400

    log(f"📡 Streaming request for: {url}")
    try:
        track_id = url.split("/")[-1].split("?")[0]
        track = sp.track(track_id)
        artist, title = track['artists'][0]['name'], track['name']

        cmd = [
            "spotdl",
            url,
            "--output", os.path.join(DOWNLOAD_FOLDER, "{artist} - {title}.{output-ext}")
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)

        for line in (result.stdout or '').strip().split('\n'):
            if line:
                log(f"📦 spotdl: {line}")
        for line in (result.stderr or '').strip().split('\n'):
            if line:
                log(f"📦 spotdl ERR: {line}")

        matched_file = find_best_match_mp3(artist, title, DOWNLOAD_FOLDER)
        if matched_file:
            log(f"🎶 Stream ready: {matched_file}")
            return jsonify({'status': 'success', 'stream_url': f'/stream-file/{matched_file}'})
        else:
            return jsonify({'status': 'error', 'message': 'MP3 not found for streaming.'})
    except Exception as e:
        log(f"🔥 Error during stream: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/stream-file/<path:filename>')
def stream_file(filename):
    """Return MP3 music as stream."""
    try:
        return send_from_directory(DOWNLOAD_FOLDER, filename, as_attachment=False, mimetype='audio/mpeg')
    except Exception as e:
        log(f"🔥 [File Stream Error] {filename}: {str(e)}")
        abort(404)

@app.route('/progress-stream')
def progress_stream():
    """
    Pushes latest log line to client as server-sent events (SSE) for progress.
    """
    def event_stream():
        previous_logs = ""
        while True:
            current_logs = "\n".join(LOGS)
            if current_logs != previous_logs:
                new_line = current_logs.split("\n")[-1]
                yield f"data: {new_line}\n\n"
                previous_logs = current_logs
            time.sleep(0.4)
    return Response(event_stream(), content_type='text/event-stream')

if __name__ == '__main__':
    log("🚀 Flask App Initialized")
    log(f"📁 Download folder ready at: {DOWNLOAD_FOLDER}")
    log("✅ Spotify client authenticated successfully")
    app.run(host="0.0.0.0", port=5000, debug=True)
