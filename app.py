from flask import Flask, render_template, request, jsonify, Response, send_file, send_from_directory
from spotipy.oauth2 import SpotifyClientCredentials
import spotipy, os, re, time
from io import BytesIO
from yt_dlp import YoutubeDL

# --- Add: Tor launcher with stem ---
import stem.process
import re as regex
import sys

SOCKS_PORT = 9050

if os.name == 'nt':
    TOR_PATH = os.path.join(os.getcwd(), "tor", "tor.exe")
else:
    TOR_PATH = "tor"  # system-installed tor for Linux/Railway

def print_bootstrap(line):
    if regex.search('Bootstrapped', line):
        print("[Tor]", line)

try:
    tor_process = stem.process.launch_tor_with_config(
        config={'SocksPort': str(SOCKS_PORT)},
        init_msg_handler=print_bootstrap,
        tor_cmd=TOR_PATH
    )
    print(f"[TOR] Tor launched on port {SOCKS_PORT} (pid: {tor_process.pid})")
except Exception as e:
    print(f"[TOR] Failed to launch Tor: {e}")
    sys.exit(1)
# --- End Tor launcher ---

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

# Spotify API auth
sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
    client_id=os.environ.get("SPOTIFY_CLIENT_ID"),
    client_secret=os.environ.get("SPOTIFY_CLIENT_SECRET")
))

# --- Add: Helper so all yt-dlp goes through Tor ---
def get_yt_dlp_opts(base_opts):
    opts = dict(base_opts)
    opts['proxy'] = f'socks5://127.0.0.1:{SOCKS_PORT}'
    opts.pop('cookiefile', None)  # optional: Tor doesn't need cookies
    return opts
# ---

def get_youtube_url_from_spotify(url):
    try:
        track_id = url.split("/")[-1].split("?")[0]
        track = sp.track(track_id)
        artist = track['artists'][0]['name']
        title = track['name']
        query = f"{artist} - {title} audio"
        log(f"🔍 Searching YouTube for: {query}")
        ydl_opts = {
            'quiet': True,
            'format': 'bestaudio/best',
            'noplaylist': True,
            'cookiefile': 'cookies.txt',
        }
        with YoutubeDL(get_yt_dlp_opts(ydl_opts)) as ydl:
            info = ydl.extract_info(f"ytsearch1:{query}", download=False)
            return info['entries'][0]['webpage_url']
    except Exception as e:
        log(f"❌ YouTube search failed: {str(e)}")
        return None

def download_mp3_to_memory(yt_url):
    try:
        log(f"🎧 Downloading: {yt_url}")
        buffer = BytesIO()
        ydl_opts = {
            'format': 'bestaudio/best',
            'cookiefile': 'cookies.txt',
            'outtmpl': '%(title)s.%(ext)s',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'quiet': True,
            'noplaylist': True,
            'logtostderr': False,
            'progress_hooks': [lambda d: log(f"📦 {d['status']}: {d.get('filename', '')}")],
        }

        with YoutubeDL(get_yt_dlp_opts(ydl_opts)) as ydl:
            info = ydl.extract_info(yt_url, download=False)
            ydl.download([yt_url])
            mp3_filename = f"{info['title']}.mp3"
            if os.path.exists(mp3_filename):
                with open(mp3_filename, 'rb') as f:
                    buffer.write(f.read())
                os.remove(mp3_filename)
                buffer.seek(0)
                return buffer
            else:
                log("❌ Expected MP3 file not found.")
        return None
    except Exception as e:
        log(f"❌ MP3 download failed: {str(e)}")
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

    yt_url = get_youtube_url_from_spotify(url)
    if not yt_url:
        return jsonify({'status': 'error', 'message': 'Could not find YouTube URL.'})

    try:
        log(f"🎧 Downloading: {yt_url}")
        ydl_opts = {
            'format': 'bestaudio/best',
            'cookiefile': 'cookies.txt',
            'outtmpl': os.path.join(DOWNLOAD_FOLDER, '%(title)s.%(ext)s'),
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'quiet': True,
            'noplaylist': True,
            'logtostderr': False,
            'progress_hooks': [lambda d: log(f"📦 {d['status']}: {d.get('filename', '')}")],
        }

        with YoutubeDL(get_yt_dlp_opts(ydl_opts)) as ydl:
            info = ydl.extract_info(yt_url, download=True)
            raw_title = info['title']
            filename = sanitize_filename(raw_title) + ".mp3"
            file_path = os.path.join(DOWNLOAD_FOLDER, filename)

            if os.path.exists(file_path):
                # ✅ Return both stream and download links
                return jsonify({
                    'status': 'success',
                    'title': raw_title,
                    'file_url': f"/download-file/{filename}",
                    'stream_url': f"/stream-file/{filename}"
                })
            else:
                log("❌ File not found after download.")
                return jsonify({'status': 'error', 'message': 'File not found after download'}), 500

    except Exception as e:
        log(f"❌ Error during download: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/download-file/<path:filename>')
def download_file(filename):
    return send_from_directory(DOWNLOAD_FOLDER, filename, as_attachment=True)

@app.route('/stream-file/<path:filename>')
def stream_file(filename):
    return send_from_directory(DOWNLOAD_FOLDER, filename, as_attachment=False)

@app.route('/stream', methods=['POST'])
def stream():
    url = request.form.get('url')
    if not url:
        return jsonify({'status': 'error', 'message': 'No track URL provided'}), 400

    yt_url = get_youtube_url_from_spotify(url)
    if not yt_url:
        return jsonify({'status': 'error', 'message': 'Could not find YouTube URL.'})

    mp3_data = download_mp3_to_memory(yt_url)
    if mp3_data:
        return send_file(mp3_data, mimetype="audio/mpeg", as_attachment=False)
    else:
        return jsonify({'status': 'error', 'message': 'MP3 not streamable'}), 500

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
    port = int(os.environ.get('PORT', 5000))  # For Railway compatibility
    log("🚀 Flask App Initialized")
    log("✅ Spotify client authenticated successfully")
    app.run(host="0.0.0.0", port=port, debug=True)
