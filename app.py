from flask import Flask, render_template, request, jsonify, send_from_directory, Response
from spotipy.oauth2 import SpotifyClientCredentials
import spotipy, subprocess, os, re, time

# Ensure ffmpeg path
os.environ["PATH"] += os.pathsep + os.path.abspath("ffmpeg")

app = Flask(__name__)
DOWNLOAD_FOLDER = os.path.join(os.getcwd(), "downloads")
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)
LOGS = []

def log(msg):
    print(msg)
    LOGS.append(msg)
    if len(LOGS) > 100:
        LOGS.pop(0)

def sanitize_filename(name):
    return re.sub(r'[\\/:"*?<>|]+', '-', name)

def download_track(url):
    try:
        track_id = url.split("/")[-1].split("?")[0]
        track = sp.track(track_id)
        artist = track['artists'][0]['name']
        title = track['name']
        safe_filename = sanitize_filename(f"{artist} - {title}.mp3")
        output_path = os.path.join(DOWNLOAD_FOLDER, safe_filename)

        cmd = ["spotdl", url, "--output", output_path]
        result = subprocess.run(cmd, capture_output=True, text=True)

        for line in result.stdout.strip().split('\n'):
            log(f"📦 spotdl: {line}")
        for line in result.stderr.strip().split('\n'):
            log(f"📦 spotdl ERR: {line}")

        if os.path.exists(output_path):
            return safe_filename
        else:
            return None
    except Exception as e:
        log(f"🔥 Error in download_track: {str(e)}")
        return None

# Initialize Spotify API
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
    url = request.form.get('url')
    if not url:
        return jsonify({'status': 'error', 'message': 'No track URL provided'}), 400

    log(f"🎧 Downloading track: {url}")
    filename = download_track(url)
    if filename:
        log(f"✅ File ready: {filename}")
        return jsonify({
            'status': 'success',
            'file': filename,
            'download_url': f'/download-file/{filename}'
        })
    else:
        log("❌ MP3 not found after download.")
        return jsonify({'status': 'error', 'message': 'MP3 not found after download.'})

@app.route('/download-file/<filename>')
def download_file(filename):
    return send_from_directory(DOWNLOAD_FOLDER, filename, as_attachment=True)

@app.route('/stream', methods=['POST'])
def stream():
    url = request.form.get('url')
    if not url:
        return jsonify({'status': 'error', 'message': 'No track URL provided'}), 400

    log(f"📡 Streaming request for: {url}")
    filename = download_track(url)
    if filename:
        log(f"🎶 Stream ready: {filename}")
        return jsonify({
            'status': 'success',
            'stream_url': f'/stream-file/{filename}'
        })
    else:
        log("❌ MP3 not found for streaming.")
        return jsonify({'status': 'error', 'message': 'MP3 not found for streaming.'})

@app.route('/stream-file/<filename>')
def stream_file(filename):
    return send_from_directory(DOWNLOAD_FOLDER, filename, as_attachment=False, mimetype='audio/mpeg')

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
    log(f"📁 Download folder ready at: {DOWNLOAD_FOLDER}")
    log("✅ Spotify client authenticated successfully")
    app.run(host="0.0.0.0", port=5000, debug=True)
