from flask import Flask, render_template, request, jsonify, Response, send_from_directory
import os, re, time, subprocess
from spotipy.oauth2 import SpotifyClientCredentials
import spotipy

app = Flask(__name__)
LOGS = []
DOWNLOAD_FOLDER = "static"

os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

def log(msg):
    print(msg)
    LOGS.append(msg)
    if len(LOGS) > 100:
        LOGS.pop(0)

def sanitize_filename(name):
    return re.sub(r'[\\/:"*?<>|]+', '-', name)

# Helper to call SDMUSIC to download first search result
def download_song_sdmusic(query, output_dir, platform="qq"):
    log(f"🎧 Using SDMUSIC to search and download: {query} (platform: {platform})")
    # 1. Search (optional, but SDMUSIC requires search to determine -i for most accurate downloads)
    # 2. Download first result
    cli_cmd = [
        "sdmusic",
        "-n", query,
        "-p", platform,
        "-d",   # download mode
        "-i", "1", # always pick the first result (user could customize!)
        "-o", output_dir
    ]
    log(f"⚙️ Running: {' '.join(cli_cmd)}")
    try:
        proc = subprocess.run(
            cli_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=180
        )
        log(proc.stdout.strip())
        if proc.returncode == 0:
            log("✅ SDMUSIC download completed.")
            return True
        else:
            log(f"❌ SDMUSIC CLI error: {proc.stderr.strip()}")
            return None
    except Exception as e:
        log(f"❌ SDMUSIC subprocess error: {e}")
        return None

# Spotify API setup (used for search only)
sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
    client_id=os.environ.get("SPOTIFY_CLIENT_ID"),
    client_secret=os.environ.get("SPOTIFY_CLIENT_SECRET")
))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/logs')
def logs():
    return jsonify(LOGS)

@app.route('/search', methods=['POST'])
def search():
    query = request.form.get('query')
    if not query:
        return jsonify({'status': 'error', 'message': 'No query provided'}), 400
    log(f"🔎 Searching Spotify for: {query}")
    try:
        results = sp.search(q=query, limit=4, type='track')
        items = results['tracks']['items']
        if not items:
            return jsonify({'status': 'error', 'message': 'No results found.'})

        choices = [{
            'name': f"{track['artists'][0]['name']} - {track['name']}",
            'url': track['external_urls']['spotify']
        } for track in items]

        return jsonify({'status': 'success', 'choices': choices})
    except Exception as e:
        log(f"🔥 Spotify search error: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/download', methods=['POST'])
def download():
    spotify_url = request.form.get('url')
    if not spotify_url:
        return jsonify({'status': 'error', 'message': 'No Spotify track URL provided'}), 400

    # Extract Spotify track info to form the search query
    try:
        track_id = spotify_url.split("/")[-1].split("?")[0]
        track_info = sp.track(track_id)
        artist_name = track_info['artists'][0]['name']
        track_name = track_info['name']
        search_query = f"{artist_name} - {track_name}"
        log(f"🎼 Resolved track info: {search_query}")
    except Exception as e:
        log(f"❌ Failed to resolve Spotify track info: {e}")
        return jsonify({'status': 'error', 'message': 'Invalid Spotify URL or API error'}), 400

    # Download with SDMUSIC (from QQ music by default)
    success = download_song_sdmusic(search_query, DOWNLOAD_FOLDER, platform="qq")
    if not success:
        return jsonify({'status': 'error', 'message': 'Download failed or SDMUSIC not installed.'}), 500

    # Find latest mp3/flac file
    files = [f for f in os.listdir(DOWNLOAD_FOLDER) if f.lower().endswith(('.mp3', '.flac'))]
    if not files:
        log("❌ No audio file found after SDMUSIC download.")
        return jsonify({'status': 'error', 'message': 'No file found after download.'}), 500
    files.sort(key=lambda f: os.path.getmtime(os.path.join(DOWNLOAD_FOLDER, f)), reverse=True)
    latest_file = files[0]

    return jsonify({
        'status': 'success',
        'title': sanitize_filename(latest_file.rsplit('.', 1)[0]),
        'file_url': f"/download-file/{latest_file}",
        'stream_url': f"/stream-file/{latest_file}"
    })

@app.route('/download-file/<path:filename>')
def download_file(filename):
    return send_from_directory(DOWNLOAD_FOLDER, filename, as_attachment=True)

@app.route('/stream-file/<path:filename>')
def stream_file(filename):
    return send_from_directory(DOWNLOAD_FOLDER, filename, as_attachment=False)

@app.route('/progress-stream')
def progress_stream():
    def event_stream():
        previous_logs = ""
        while True:
            current_logs = "\n".join(LOGS)
            if current_logs != previous_logs:
                new_line = current_logs.split("\n")[-1]
                yield f"data: {new_line}\n\n"
                previous_logs = current_logs
            time.sleep(0.5)
    return Response(event_stream(), content_type='text/event-stream')

if __name__ == '__main__':
    log("🚀 Flask App Initialized")
    app.run(host="0.0.0.0", port=5000, debug=True)
