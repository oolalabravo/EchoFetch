from flask import Flask, render_template, request, jsonify, send_from_directory
from spotipy.oauth2 import SpotifyClientCredentials
import spotipy, subprocess, os, glob

app = Flask(__name__)
DOWNLOAD_FOLDER = os.path.join(os.getcwd(), r"F:\programs\Spotify_songs\downloads")
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)
LOGS = []

def log(msg):
    print(msg)
    LOGS.append(msg)
    if len(LOGS) > 100:
        LOGS.pop(0)

sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
    client_id='78ea7eb921f847bd8c74c4320782f3ab',
    client_secret='e3a16c4eeca6445a8526ea32caef4c35'
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

    try:
        cmd = [r"C:\Users\intel\AppData\Roaming\Python\Python313\Scripts\spotdl.exe",
               url, "--output", os.path.join(DOWNLOAD_FOLDER, "{artist} - {title}.{output-ext}")]
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.stdout:
            log(f"📦 spotdl stdout: {result.stdout}")
        if result.stderr:
            log(f"📦 spotdl stderr: {result.stderr}")

        files = glob.glob(os.path.join(DOWNLOAD_FOLDER, "*.mp3"))
        if not files:
            return jsonify({'status': 'error', 'message': 'File not downloaded.'})

        latest_file = max(files, key=os.path.getctime)
        filename = os.path.basename(latest_file)
        log(f"✅ File ready: {filename}")

        return jsonify({
            'status': 'success',
            'file': filename,
            'download_url': f'/download-file/{filename}'
        })

    except Exception as e:
        log(f"🔥 Error during download: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/download-file/<filename>')
def download_file(filename):
    return send_from_directory(DOWNLOAD_FOLDER, filename, as_attachment=True)

if __name__ == '__main__':
    log("🚀 Flask App Initialized")
    log(f"📁 Download folder ready at: {DOWNLOAD_FOLDER}")
    log("✅ Spotify client authenticated successfully")
    app.run(host="0.0.0.0", port=5000)
