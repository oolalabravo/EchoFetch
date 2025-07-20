from flask import Flask, render_template, request, jsonify, Response, send_from_directory
import os, re, time, subprocess, shutil
from spotipy.oauth2 import SpotifyClientCredentials
import spotipy


app = Flask(__name__)
LOGS = []
DOWNLOAD_FOLDER = "static"

# Create download folder if not exists
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

def log(msg):
    print(msg)
    LOGS.append(msg)
    if len(LOGS) > 100:
        LOGS.pop(0)

def sanitize_filename(name):
    return re.sub(r'[\\/:"*?<>|]+', '-', name)

def download_song(query, output_dir):
    log(f"🎧 Using MusicDL CLI to search and download: {query}")

    cli_cmd = [
        'musicdl',
        '-s', query,
        '--savedir', output_dir,
        '--logfilepath', os.path.join(output_dir, 'musicdl.log'),
        '--search_size_per_source', '5',
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
            log("✅ MusicDL download completed.")
            return True
        else:
            log(f"❌ MusicDL CLI error: {proc.stderr.strip()}")
            return None
    except Exception as e:
        log(f"❌ MusicDL subprocess error: {e}")
        return None



# Spotify API (for search, not downloading)
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

    # Extract track info from Spotify
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

    # Download using scdl with refined search
    success = download_song(search_query, DOWNLOAD_FOLDER)
    if not success:
        return jsonify({'status': 'error', 'message': 'Download failed or scdl not installed.'}), 500

    # Find most recent mp3 file
    files = [f for f in os.listdir(DOWNLOAD_FOLDER) if f.lower().endswith('.mp3')]
    if not files:
        log("❌ No MP3 files found after scdl download.")
        return jsonify({'status': 'error', 'message': 'No MP3 file found after download.'}), 500
    files = sorted(files, key=lambda f: os.path.getmtime(os.path.join(DOWNLOAD_FOLDER, f)), reverse=True)
    latest_file = files[0]

    return jsonify({
        'status': 'success',
        'title': sanitize_filename(latest_file.replace('.mp3', '')),
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
