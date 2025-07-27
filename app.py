from flask import Flask, request, render_template_string, send_file
import subprocess
import tempfile
import shutil
import glob
import os
import io
import requests

app = Flask(__name__)
CLIENT_ID = "CCbVVppXByCBrh4OcGmbrgyYhni0SgvL"

INDEX_HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>SoundCloud Downloader</title>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap" rel="stylesheet">
  <style>
    body {
      font-family: 'Inter', sans-serif;
      background: linear-gradient(135deg, #ff5500, #ff9966);
      color: #fff;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      height: 100vh;
      margin: 0;
    }
    h1 {
      font-size: 3em;
      font-weight: 800;
      margin-bottom: 20px;
    }
    form {
      background: rgba(0, 0, 0, 0.6);
      padding: 30px;
      border-radius: 15px;
      box-shadow: 0 8px 20px rgba(0,0,0,0.3);
    }
    input[type="text"] {
      padding: 12px;
      font-size: 1.1em;
      border: none;
      border-radius: 8px;
      width: 300px;
      margin-right: 10px;
    }
    input[type="submit"] {
      background: #fff;
      color: #ff5500;
      font-weight: 600;
      border: none;
      padding: 12px 20px;
      border-radius: 8px;
      cursor: pointer;
      transition: 0.3s;
    }
    input[type="submit"]:hover {
      background: #ffe6d5;
    }
  </style>
</head>
<body>
  <h1>SoundCloud Downloader</h1>
  <form method="post" action="/search">
    <input type="text" name="song_name" placeholder="Enter song name" required>
    <input type="submit" value="Search">
  </form>
</body>
</html>
"""


SEARCH_RESULTS_HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Search Results</title>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap" rel="stylesheet">
  <style>
    body {
      font-family: 'Inter', sans-serif;
      background: #f8f8f8;
      color: #333;
      padding: 40px;
    }
    h1 {
      color: #ff5500;
      font-weight: 700;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      margin-top: 20px;
    }
    th, td {
      padding: 12px 15px;
      text-align: left;
      border-bottom: 1px solid #ddd;
    }
    th {
      background-color: #ff5500;
      color: white;
    }
    tr:hover {
      background-color: #ffe6d5;
    }
    form {
      max-width: 800px;
      margin: auto;
    }
    input[type="submit"] {
      margin-top: 20px;
      background-color: #ff5500;
      color: white;
      font-weight: 600;
      padding: 12px 20px;
      border: none;
      border-radius: 8px;
      cursor: pointer;
      transition: 0.3s;
    }
    input[type="submit"]:hover {
      background-color: #e64a00;
    }
    .error {
      color: red;
      margin-bottom: 20px;
    }
    a {
      display: inline-block;
      margin-top: 30px;
      text-decoration: none;
      color: #ff5500;
      font-weight: 600;
    }
    a:hover {
      text-decoration: underline;
    }
  </style>
</head>
<body>
  <h1>Search results for '{{ query }}'</h1>
  {% if error %}<p class="error">{{ error }}</p>{% endif %}
  <form method="post" action="/stream">
    <table>
      <tr><th>No.</th><th>Title</th><th>Artist</th><th>Select</th></tr>
      {% for t in tracks %}
      <tr>
        <td>{{ t.no }}</td>
        <td>{{ t.title }}</td>
        <td>{{ t.artist }}</td>
        <td><input type="radio" name="song_no" value="{{ t.no }}" required></td>
      </tr>
      {% endfor %}
    </table>
    <input type="hidden" name="query" value="{{ query }}">
    <input type="submit" value="Stream Selected Song">
  </form>
  <a href="/">🔙 Search again</a>
</body>
</html>
"""


# Store song links in memory temporarily
stored_links = {}

def fetch(query):
    url = f"https://api-v2.soundcloud.com/search/tracks?q={query}&client_id={CLIENT_ID}&limit=3"
    res = requests.get(url)
    if res.status_code != 200:
        return None, f"Error: {res.status_code} {res.text}"

    data = res.json()
    tracks = []
    links = []

    for idx, track in enumerate(data.get("collection", []), start=1):
        tracks.append({
            'no': idx,
            'title': track['title'],
            'artist': track['user']['username'],
            'url': track['permalink_url']
        })
        links.append(track['permalink_url'])

    return tracks, links

def download_song_to_memory(link):
    scdl_path = shutil.which("scdl")
    if not scdl_path:
        return None, "❌ 'scdl' not found in PATH."

    with tempfile.TemporaryDirectory() as tmpdir:
        command = [scdl_path, "-l", link, "--path", tmpdir]
        result = subprocess.run(command, capture_output=True, text=True)

        if result.returncode != 0:
            return None, result.stderr

        audio_files = []
        for ext in ('*.mp3', '*.m4a', '*.flac', '*.wav'):
            audio_files += glob.glob(os.path.join(tmpdir, ext))

        if not audio_files:
            return None, "⚠️ No audio file found."

        filepath = audio_files[0]
        with open(filepath, "rb") as f:
            song_bytes = io.BytesIO(f.read())
            song_bytes.seek(0)
            return (song_bytes, os.path.basename(filepath)), "✅ Stream ready"

@app.route("/")
def index():
    return INDEX_HTML

@app.route("/search", methods=["POST"])
def search():
    query = request.form.get("song_name", "").strip()
    if not query:
        return render_template_string(SEARCH_RESULTS_HTML, query=query, tracks=[], error="Please enter a song name.")

    tracks, links = fetch(query)
    if not tracks:
        return render_template_string(SEARCH_RESULTS_HTML, query=query, tracks=[], error=links)

    stored_links[query] = links
    return render_template_string(SEARCH_RESULTS_HTML, query=query, tracks=tracks, error=None)

@app.route("/stream", methods=["POST"])
def stream():
    query = request.form.get("query", "")
    song_no = request.form.get("song_no")

    if query not in stored_links:
        return "⚠️ Session expired or invalid query."

    try:
        song_idx = int(song_no) - 1
        link = stored_links[query][song_idx]
    except Exception:
        return "⚠️ Invalid selection."

    result, msg = download_song_to_memory(link)
    if result:
        song_bytes, filename = result
        return send_file(song_bytes, as_attachment=True, download_name=filename)
    return f"❌ Error:\n{msg}", 500

if __name__ == "__main__":
    app.run(debug=True)
