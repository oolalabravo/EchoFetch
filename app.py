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

def download_with_manzana(apple_music_url, output_dir):
    log(f"🎧 Using Manzana to download: {apple_music_url}")
    cmd = ["python", "manzana.py", apple_music_url]

    try:
        result = subprocess.run(
            cmd,
            cwd=os.path.abspath("."),  # run from project root
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=300
        )
        log(result.stdout)
        if result.returncode == 0:
            log("✅ Manzana download completed.")
            return True
        else:
            log(f"❌ Manzana CLI error: {result.stderr.strip()}")
            return False
    except Exception as e:
        log(f"❌ Manzana subprocess exception: {e}")
        return False

# Spotify API
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
        choices = []
        for track in items:
            artist = track['artists'][0]['name']
            name = track['name']
            url = track['external_urls']['spotify']
            apple_guess = f"https://music.apple.com/search?term={artist.replace(' ', '+')}+{name.replace(' ', '+')}"
            choices.append({'name': f"{artist} - {name}", 'url': url, 'apple_hint': apple_guess})
        return jsonify({'status': 'success', 'choices': choices})
    except Exception as e:
        log(f"🔥 Spotify search error: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/download', methods=['POST'])
def download():
    apple_music_url = request.form.get('apple_url')
    if not apple_music_url:
        return jsonify({'status': 'error', 'message': 'No Apple Music URL provided'}), 400

    log(f"🎯 Using Apple Music URL: {apple_music_url}")
    success = download_with_manzana(apple_music_url, DOWNLOAD_FOLDER)
    if not success:
        return jsonify({'status': 'error', 'message': 'Download failed using Manzana.'}), 500

    files = [f for f in os.listdir(DOWNLOAD_FOLDER) if f.lower().endswith(('.m4a', '.mp4'))]
    if not files:
        log("❌ No downloadable files found after Manzana run.")
        return jsonify({'status': 'error', 'message': 'No files found after download.'}), 500
    latest_file = sorted(files, key=lambda f: os.path.getmtime(os.path.join(DOWNLOAD_FOLDER, f)), reverse=True)[0]

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
