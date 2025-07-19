from flask import Flask, render_template, request, jsonify, Response, send_file
from spotipy.oauth2 import SpotifyClientCredentials
import spotipy, os, re, time
from io import BytesIO
from yt_dlp import YoutubeDL

app = Flask(__name__)
LOGS = []

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
        with YoutubeDL(ydl_opts) as ydl:
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

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(yt_url, download=False)
            ydl.download([yt_url])
            # Find the expected filename (usually sanitized title + .mp3)
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

    mp3_data = download_mp3_to_memory(yt_url)
    if mp3_data:
        filename = sanitize_filename(yt_url.split("=")[-1]) + ".mp3"
        return send_file(mp3_data, mimetype="audio/mpeg", as_attachment=True, download_name=filename)
    else:
        return jsonify({'status': 'error', 'message': 'MP3 not available'}), 500

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
    log("🚀 Flask App Initialized")
    log("✅ Spotify client authenticated successfully")
    app.run(host="0.0.0.0", port=5000, debug=True)
