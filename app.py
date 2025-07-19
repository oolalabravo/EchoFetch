from flask import Flask, render_template, request, jsonify, Response, send_file, send_from_directory
from spotipy.oauth2 import SpotifyClientCredentials
import spotipy, os, re, time, random
from io import BytesIO
import subprocess
import shutil
import requests
from bs4 import BeautifulSoup

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

# Spotify API auth (for search/track/metadata features)
sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
    client_id=os.environ.get("SPOTIFY_CLIENT_ID"),
    client_secret=os.environ.get("SPOTIFY_CLIENT_SECRET")
))

def scdl_download(url, output_dir):
    """Downloads track/playlist/artist from SoundCloud using scdl CLI"""
    if shutil.which("scdl") is None:
        log("❌ scdl CLI not found. Install it by running: pip install scdl")
        return None
    cmd = ["scdl", "-l", url, "--path", output_dir, "--onlymp3"]
    try:
        log(f"🎧 Running scdl download for: {url}")
        completed = subprocess.run(cmd, capture_output=True, text=True, check=True)
        log(f"📥 scdl output: {completed.stdout}")
        log("✅ scdl download completed")
        return True
    except subprocess.CalledProcessError as e:
        log(f"❌ scdl download failed: {e.stderr}")
        return None

def get_spotify_song_details(spotify_url):
    try:
        track_id = spotify_url.split("/")[-1].split("?")[0]
        track = sp.track(track_id)
        artist = track['artists'][0]['name']
        title = track['name']
        return title, artist
    except Exception as e:
        log(f"❌ Spotify error: {e}")
        return None, None

def search_soundcloud_track_url(query):
    """Search SoundCloud via web scraping for the first track url matching the query."""
    log(f"🔍 Searching SoundCloud for: {query}")
    search_url = f"https://soundcloud.com/search/sounds?q={requests.utils.quote(query)}"
    resp = requests.get(search_url, headers={
        "User-Agent": "Mozilla/5.0"
    })
    soup = BeautifulSoup(resp.text, "html.parser")
    # Find all links that look like track links: "/artistname/trackname"
    for link in soup.find_all('a', href=True):
        href = link['href']
        if href.startswith("/") and len(href.split("/")) == 3 and not href.startswith('/you/') and not ':' in href:
            # Form a full link
            full_url = f"https://soundcloud.com{href}"
            log(f"🔎 Found SoundCloud track: {full_url}")
            return full_url
    log("❌ No SoundCloud track found")
    return None

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

    # If it's a Spotify link, resolve details then search SoundCloud!
    if "open.spotify.com/track" in url:
        title, artist = get_spotify_song_details(url)
        if not (title and artist):
            return jsonify({'status': 'error', 'message': 'Failed to get song details from Spotify'}), 500
        sc_search_query = f"{artist} {title}"
        soundcloud_url = search_soundcloud_track_url(sc_search_query)
        if not soundcloud_url:
            return jsonify({'status': 'error', 'message': 'Could not find track on SoundCloud'}), 404
        url = soundcloud_url

    # url is now a SoundCloud link!
    success = scdl_download(url, DOWNLOAD_FOLDER)
    if not success:
        return jsonify({'status': 'error', 'message': 'Download failed or scdl not installed.'}), 500
    # Find most recent mp3 file in the DOWNLOAD_FOLDER
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
    log("✅ Spotify client authenticated successfully")
    app.run(host="0.0.0.0", port=5000, debug=True)
