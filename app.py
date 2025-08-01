from flask import Flask, request, render_template_string, send_file
import subprocess
import tempfile
import shutil
import glob
import io
import requests
import lyricsgenius
import os
import time
from colorthief import ColorThief

app = Flask(__name__)
CLIENT_ID = "CLIENT_ID"

# Initialize Genius client with increased timeout
GENIUS_ACCESS_TOKEN = "GENIUS_TOKEN"
genius = lyricsgenius.Genius(GENIUS_ACCESS_TOKEN, timeout=15)
genius.skip_non_songs = True
genius.excluded_terms = ["(Remix)", "(Live)"]
genius.remove_section_headers = True
song_name = ''

# ========== HTML TEMPLATES ==========

INDEX_HTML = '''
<!doctype html>
<html lang="en">
<head>
  <link rel="icon" type="image/x-icon" href="icon.ico" />

  <meta charset="UTF-8" />
  <title>SoundCloud Downloader</title>
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&family=Material+Symbols+Rounded" rel="stylesheet" />
  <style>
    body { background: linear-gradient(135deg, #ff5500 0, #ffb066 100%); min-height: 100vh; margin: 0; font-family: 'Inter', sans-serif; display: flex; justify-content: center; align-items: center; flex-direction: column; animation: hueRotate 16s infinite linear;}
    @keyframes hueRotate {0% {filter: hue-rotate(0deg);} 100% {filter: hue-rotate(12deg);}}
    .glass-card { background: rgba(255,255,255, .18); box-shadow: 0 8px 32px 0 rgba(31,38,135,0.15); backdrop-filter: blur(7.5px); border-radius: 32px; padding: 50px 40px 30px 40px; border: 1.5px solid rgba(255,255,255,0.32); animation: fadeUp 1s cubic-bezier(.79,-0.1,.17,1.06);}
    @keyframes fadeUp {0% {opacity:0;transform:translateY(10vh);}100%{opacity:1;transform:translateY(0);}}
    h1 {font-size: 2.8rem; font-weight: 800; text-align: center; letter-spacing: -2px; margin: 0 0 16px 0; color: #fff; text-shadow: 0 1.5px 0 #ff7222; line-height: 1.1;}
    form { display: flex; flex-direction: column; gap: 18px; align-items: center; width: 260px; margin: 0 auto;}
    .input-wrap {display: flex;width: 100%;position: relative;}
    input[type="text"] {width: 100%;border: none; border-radius: 9999px; padding: 13px 48px 13px 22px; font-size: 1.1rem; outline: none; background: rgba(255,255,255,0.87); color: #e24d00; font-weight: 600; transition: box-shadow 0.2s; box-shadow: 0 2px 8px #ff550014;}
    input[type="text"]:focus { box-shadow: 0 2px 16px #ff550050;}
    .material-symbols-rounded {position: absolute; right: 14px;top: 50%;transform: translateY(-50%);color: #ff5500cc;font-size: 1.66em;pointer-events: none;user-select: none;}
    button, input[type="submit"] { border: none; background: linear-gradient(90deg,#ff6600 80%,#ffae51 100%); color: #fff; font-weight: 800; font-size: 1.13rem; letter-spacing: 0.5px; border-radius: 9999px; padding: 12px 38px; cursor: pointer; transition: box-shadow .23s, background .2s; box-shadow: 0 2px 10px #ff550035; margin-top: 8px; position: relative; overflow: hidden; z-index: 1;}
    button:active, input[type="submit"]:active {transform: scale(.99);}
    button:hover, input[type="submit"]:hover { background: linear-gradient(90deg,#ff6600 85%,#ffd7b1 100%); box-shadow:0 4px 16px #ff955010;}
    .ripple { position: absolute; background: rgba(255,255,255,0.3); border-radius: 50%; pointer-events: none; animation: ripple 0.48s linear; z-index: 2;}
    @keyframes ripple {100% { transform: scale(2.3); opacity: 0;}}
    @media (max-width: 650px) { .glass-card {padding: 28px 10px 20px 10px;} h1 {font-size: 2rem;} form {width: 93vw;} input[type="text"] {font-size: 1rem;}}
    .footer {color: #fff9; font-weight: 600; text-align: center; margin-top: 3vw; font-size: 1.05em; letter-spacing: .01em; user-select: none; opacity: 0.7;}
  </style>
</head>
<body>
  <div class="glass-card">
    <h1><span class="material-symbols-rounded" style="vertical-align:-4px;font-size:1.13em;margin-right:-2px;">audiotrack</span> SoundCloud Downloader</h1>
    <form method="post" action="/search" autocomplete="off">
      <div class="input-wrap">
        <input type="text" name="song_name" placeholder="Enter song name" required autofocus />
        <span class="material-symbols-rounded">search</span>
      </div>
      <input type="submit" value="Search" />
    </form>
  </div>
  <div class="footer">
  <span>
    &#127926; Built with <b>Flask</b> &amp; SoundCloud API |
    <a href="https://soundcloud.com" style="color:#fff;text-decoration:underline;font-weight:400;">Listen on SoundCloud</a>
    <br>
    <span style="font-size:0.97em;">View source on
      <a href="https://github.com/oolalabravo/EchoFetch" style="color:#fff;text-decoration:underline;font-weight:600;">GitHub &mdash; oolalabravo/EchoFetch</a>
    </span>
  </span>
</div>

  <script>
    document.addEventListener('DOMContentLoaded', () => {
      document.querySelectorAll('button, input[type="submit"]').forEach(el => {
        el.addEventListener('click', function(e) {
          const circle = document.createElement('span');
          circle.className = 'ripple';
          const d = Math.max(this.clientWidth, this.clientHeight);
          circle.style.width = circle.style.height = d + 'px';
          circle.style.left = (e.offsetX - d/2) + 'px';
          circle.style.top = (e.offsetY - d/2) + 'px';
          this.appendChild(circle);
          circle.addEventListener('animationend', () => circle.remove());
        });
      });
    });
  </script>
</body>
</html>
'''

SEARCH_RESULTS_HTML = '''
<!doctype html>
<html lang="en">
<head>
  <link rel="icon" type="image/png" href="icon.ico" />
  <meta charset="UTF-8" />
  <title>Search Results</title>
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&family=Material+Symbols+Rounded" rel="stylesheet" />
  <style>
    body {
      min-height: 100vh;
      background: linear-gradient(137deg, #ff661a 25%, #ffbb7b 74%);
      font-family: 'Inter', sans-serif;
      margin: 0;
      padding: 0;
      animation: hueRotate 16s infinite linear;
    }
    @keyframes hueRotate {
      0% { filter: hue-rotate(0deg); }
      100% { filter: hue-rotate(10deg); }
    }
    h1 {
      color: #ff5500; font-size: 2.2em; font-weight: 800;
      letter-spacing: -.8px; text-shadow: 0 1px 0 #fff5;
      margin: 36px 0 18px 0; text-align: center;
    }
    .results-wrap {
      max-width: 900px;
      margin: auto;
      background: rgba(255,255,255,0.81);
      border-radius: 24px;
      box-shadow: 0 6px 36px #ff55001c;
      padding: 38px 32px 34px;
      margin-top: 2vw;
      animation: fadeUp 0.83s cubic-bezier(.79,-0.13,.18,1.15);
      /* Make it relative for ripple layers if needed */
      position: relative;
    }
    @keyframes fadeUp {
      0% { opacity: 0; transform: translateY(3vh); }
      100% { opacity: 1; transform: translateY(0); }
    }

    /* Fade-out animation upon song selection */
    .fade-out {
      animation: fadeOut 0.5s forwards;
    }
    @keyframes fadeOut {
      to {
        opacity: 0;
        transform: translateY(20px);
      }
    }

    .error {
      color: #da3636;
      font-weight: 700;
      background: #ffe8e1;
      border-radius: 11px;
      padding: 9px 14px 7px 32px;
      margin-bottom: 20px;
      border-left: 4px solid #ff5500;
      font-size: 1.01em;
    }
    .results-table {
      width: 100%;
      border-collapse: separate;
      border-spacing: 0 9px;
    }
    th, td {
      text-align: left;
      padding: 13px 8px;
      font-size: 1.08em;
    }
    th {
      background: #ff5500 linear-gradient(90deg,#ff5500 93%,#ffbb7b 175%);
      color: #fff;
      font-weight: 800;
      letter-spacing: .05em;
      border-radius: 7px 7px 0 0;
      text-shadow: 0 1.2px 0 #df6c09c2;
    }
    tr.result-row {
      background: linear-gradient(96deg, #fff7 90%, #fff3 130%);
      border-radius: 15px;
      box-shadow: 0 1.6px 8px #ffb27218;
      border: none;
      transition: box-shadow .2s;
    }
    tr.result-row:hover {
      box-shadow: 0 4px 18px #ff6e1e19, 0 0 0 2px #ffae517c;
      background: #ffefd6c2;
    }
    .cover {
      width: 54px;
      height: 54px;
      object-fit: cover;
      border-radius: 11px;
      margin-right: 11px;
      box-shadow: 0 1.5px 7px #bc44031a;
      background: #ffccab4f;
      transition: filter .18s;
      filter: saturate(1.12);
    }
    .track-meta {
      display: flex;
      flex-direction: row;
      align-items: center;
    }
    .track-title {
      font-weight: 700;
      color: #e24d00;
      font-size: 1.09em;
      letter-spacing: -.01em;
      margin-bottom: 2px;
      text-wrap: balance;
      text-shadow: 0 1px 0 #fff7;
    }
    .track-artist {
      font-size: .99em;
      color: #383232c5;
      opacity: 0.93;
      margin-bottom: 1.5px;
      margin-left: 2.5px;
    }
    .actions {
      display: flex;
      gap: 8px;
    }
    button {
      border: none;
      border-radius: 999px;
      font-weight: 700;
      padding: 9px 20px 9px 18px;
      margin-left: 3px;
      background: linear-gradient(90deg, #ff5500 89%, #ffba7c 141%);
      color: #fff;
      font-size: 1em;
      box-shadow: 0 3px 24px #ff905028;
      cursor: pointer;
      transition: box-shadow .19s, background .18s;
      position: relative;
      overflow: hidden;
      z-index: 0;
      display: flex;
      align-items: center;
      gap: 6px;
    }
    button span.material-symbols-rounded {
      font-size: 1.24em;
      margin-right: 2px;
    }
    button:active {
      transform: scale(.99);
    }
    button:hover {
      background: linear-gradient(90deg, #ff9400 60%, #ffd9ba 100%);
      box-shadow:0 4px 22px #ffb9671a;
      color: #e24d00;
    }
    .noresults {
      color: #d94d05;
      font-weight: 600;
      margin: 25px 0;
      text-align: center;
      font-size: 1.18em;
    }
    .backlink {
      display: inline-block;
      color: #ff5500;
      font-weight: 700;
      text-decoration: none;
      margin: 26px 6px 0 0;
      font-size: 1.08em;
      transition: text-decoration .18s;
    }
    .backlink:hover {
      text-decoration: underline;
    }
    @media (max-width: 900px) {
      .results-wrap {
        padding: 20px 3vw;
      }
    }
    @media (max-width: 630px) {
      h1 {
        font-size: 1.29em;
      }
      .results-wrap {
        border-radius: 16px;
        padding: 7vw 1vw;
      }
      .cover {
        width: 38px;
        height: 38px;
      }
      th, td {
        font-size: .97em;
      }
    }

    /* Ripple effect style */
    .ripple {
      position: absolute;
      border-radius: 50%;
      background-color: rgba(255, 255, 255, 0.6);
      animation: ripple-animation 0.6s linear;
      pointer-events: none;
      transform: scale(0);
      z-index: 10;
    }
    @keyframes ripple-animation {
      to {
        transform: scale(4);
        opacity: 0;
      }
    }
  </style>
</head>
<body>
  <h1><span class="material-symbols-rounded" style="vertical-align:-4px;font-size:1.18em;color:#ffae53">search</span> Search results for '{{ query }}'</h1>
  <div class="results-wrap">
    {% if error %}
      <div class="error">{{ error }}</div>
    {% endif %}
    <form method="post" action="/stream" id="songForm">
      {% if tracks|length == 0 %}
        <div class="noresults">😔 No tracks found. Try refining your search.</div>
      {% else %}
      <table class="results-table">
        <tr>
          <th width="5%">#</th>
          <th width="58%">Track</th>
          <th width="28%">Artist</th>
          <th width="21%">Actions</th>
        </tr>
        {% for t in tracks %}
        <tr class="result-row">
          <td>{{ t.no }}</td>
          <td>
            <div class="track-meta">
              <img class="cover" src="{{ t.cover or 'https://icons.iconarchive.com/icons/papirus-team/papirus-apps/128/soundcloud-icon.png' }}" alt="cover" />
              <div>
                <span class="track-title">{{ t.title }}</span><br />
                <span class="track-artist">{{ t.artist }}</span>
              </div>
            </div>
          </td>
          <td>
            <span style="font-weight:600;">{{ t.artist }}</span>
          </td>
          <td>
            <div class="actions">
              <button type="submit" name="song_no" value="{{ t.no }}|listen"><span class="material-symbols-rounded">play_circle</span>Listen</button>
              <button type="submit" name="song_no" value="{{ t.no }}|download"><span class="material-symbols-rounded">download</span>Download</button>
            </div>
          </td>
        </tr>
        {% endfor %}
      </table>
      {% endif %}
      <input type="hidden" name="query" value="{{ query }}" />
    </form>
    <a href="/" class="backlink"><span class="material-symbols-rounded" style="vertical-align:-2px;font-size:1.15em;">arrow_back</span>Search again</a>
  </div>

  <script>
    document.addEventListener('DOMContentLoaded', () => {
      const form = document.getElementById('songForm');
      const resultsWrap = document.querySelector('.results-wrap');

      document.querySelectorAll('button[type="submit"]').forEach(button => {
        button.addEventListener('click', function(e) {
          e.preventDefault();  // Prevent normal form submission

          // Ripple effect
          const circle = document.createElement('span');
          circle.className = 'ripple';
          const d = Math.max(this.clientWidth, this.clientHeight);
          circle.style.width = circle.style.height = d + 'px';
          circle.style.left = (e.offsetX - d/2) + 'px';
          circle.style.top = (e.offsetY - d/2) + 'px';
          this.appendChild(circle);
          circle.addEventListener('animationend', () => circle.remove());

          // Add fade-out effect to container
          resultsWrap.classList.add('fade-out');

          // When fade-out animation ends, submit form with clicked button value
          resultsWrap.addEventListener('animationend', () => {
            // Set hidden input with button value to preserve which action was chosen
            let hiddenInput = form.querySelector('input[name="song_no"]');
            if (!hiddenInput) {
              hiddenInput = document.createElement('input');
              hiddenInput.type = 'hidden';
              hiddenInput.name = 'song_no';
              form.appendChild(hiddenInput);
            }
            hiddenInput.value = this.value;

            form.submit();
          }, { once: true });

        });
      });
    });
  </script>
</body>
</html>

'''

PLAYER_HTML = '''
<!doctype html>
<html>
<head>
  <link rel="icon" type="image/png" href="icon.ico" />

  <title>{{ filename }}</title>
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&family=Material+Symbols+Rounded" rel="stylesheet" />
  <style>
    :root {
      --main-bg: {{ dominant_color }};
    }
    body {
      margin: 0;
      padding: 0;
      min-height: 100vh;
      font-family: 'Inter', sans-serif;
      color: #222;
      position: relative;
      overflow-x: hidden;
      background: #fff;
    }
    body::before {
      content: "";
      position: fixed;
      top: 0; left: 0; right: 0; bottom: 0;
      background-image: url('{{ cover }}');
      background-size: cover;
      background-position: center;
      filter: blur(40px) brightness(0.6) saturate(1.3);
      transform: scale(1.05);
      z-index: -2;
    }
    body::after {
      content: "";
      position: fixed;
      top: 0; left: 0; right: 0; bottom: 0;
      background: radial-gradient(circle at center,
        var(--main-bg, #ff6600) 0%, 
        rgba(255,255,255,0.10) 90%);
      mix-blend-mode: multiply;
      z-index: -1;
      pointer-events: none;
    }
    .container {
      background: linear-gradient(115deg, var(--main-bg, #ff6600) 10%, rgba(255,255,255,0.95) 90%);
      max-width: 430px;
      margin: 8vh auto 3rem auto;
      border-radius: 26px;
      box-shadow:
        0 12px 48px var(--main-bg, #ff6600),
        0 2px 18px #ff550026;
      padding: 44px 28px 30px;
      text-align: center;
      position: relative;
      z-index: 1;
      animation: fadeUp 0.9s cubic-bezier(.79,-0.16,.24,1.18);
    }
    @keyframes fadeUp {
      0% {opacity: 0; transform: translateY(4vh);}
      100% {opacity: 1; transform: translateY(0);}
    }
    .cover {
      width: 90px;
      height: 90px;
      object-fit: cover;
      border-radius: 18px;
      margin: 14px auto 12px;
      box-shadow: 0 4px 25px var(--main-bg, #ff660088);
      display: block;
    }
    .title {
      font-weight: 800;
      font-size: 1.3em;
      color: var(--main-bg, #ff6f27);
      letter-spacing: -0.2px;
      margin-bottom: 8px;
      text-shadow: 0 1px 0 #fff8;
    }
    audio {
      width: 100%;
      border-radius: 9px;
      background: #fbf7f5;
      outline: none;
      box-shadow: 0 1.5px 8px #ff550021;
      margin: 20px 0 18px;
    }
    .lyricsbox {
      max-height: 280px;
      overflow-y: auto;
      margin-top: 24px;
      padding: 16px;
      background: #fff4e0;
      border-radius: 12px;
      color: #a64d00;
      font-family: monospace, monospace;
      white-space: pre-wrap;
      box-shadow: inset 0 2px 8px #ffb75d99;
      text-align: left;
    }
    .lyricsbox h3 {
      margin-top: 0;
      font-weight: 700;
    }
    .no-lyrics {
      margin-top: 24px;
      color: #cc6a00;
      font-style: italic;
    }
    .actions {
      margin-top: 16px;
    }
    .actions > a {
      display: inline-block;
      padding: 7px 28px 7px 17px;
      margin: 8px 6px 0 6px;
      border-radius: 99px;
      font-weight: 700;
      text-decoration: none;
      color: #fff;
      background: linear-gradient(92deg, var(--main-bg, #ff7700) 75%, #fff2 150%);
      font-size: 1.066em;
      box-shadow: 0 2px 14px var(--main-bg, #ffae3c27);
      transition: background 0.17s, color 0.15s;
      position: relative;
      overflow: hidden;
      vertical-align: middle;
    }
    .actions > a span.material-symbols-rounded {
      font-size: 1.14em;
      margin-right: 2px;
      vertical-align: -2.2px;
    }
    .actions > a:hover {
      background: linear-gradient(94deg, #ffd095 50%, var(--main-bg, #ff9400) 180%);
      color: var(--main-bg, #ff5500);
      text-decoration: underline;
    }
    @media (max-width: 600px) {
      .container {
        width: 90vw;
        padding: 22px 6vw;
      }
      .cover {
        width: 70px;
        height: 70px;
        border-radius: 14px;
      }
    }
  </style>
</head>
<body>
  <div class="container">
    {% if cover %}
      <img src="{{ cover }}" class="cover" alt="cover art" />
    {% endif %}
    <div class="title">
      <span class="material-symbols-rounded" style="font-size:.97em;vertical-align:-2px;">volume_up</span>
      Now Playing: {{ filename }}
    </div>
    <audio controls autoplay>
      <source src="/media/{{ song_id }}" type="{{ MIME }}" />
      Sorry, your browser doesn't support the audio element.
    </audio>

    {% if lyrics %}
      <div class="lyricsbox">
        <h3>Lyrics</h3>
        <pre>{{ lyrics }}</pre>
      </div>
    {% else %}
      <p class="no-lyrics">Lyrics not found.</p>
    {% endif %}

    <div class="actions">
      <a href="/"><span class="material-symbols-rounded">arrow_back</span>Search another</a>
      <a href="/media/{{ song_id }}?download=1"><span class="material-symbols-rounded">download</span>Download this file</a>
    </div>
  </div>
</body>
</html>
'''

FORBIDDEN_HTML = ''' <!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>403 Forbidden</title>
  <style>
    @import url("https://fonts.googleapis.com/css?family=Press+Start+2P");
    html, body { width: 100%; height: 100%; margin: 0; }
    * { font-family: 'Press Start 2P', cursive; box-sizing: border-box; }
    #app {
      padding: 1rem;
      background: black;
      display: flex;
      height: 100%;
      justify-content: center;
      align-items: center;
      color: #54FE55;
      text-shadow: 0px 0px 10px;
      font-size: 6rem;
      flex-direction: column;
    }
    #app .txt { font-size: 1.8rem; }
    @keyframes blink {
      0%, 49% { opacity: 0; }
      50%, 100% { opacity: 1; }
    }
    .blink {
      animation-name: blink;
      animation-duration: 1s;
      animation-iteration-count: infinite;
    }
  </style>
</head>
<body>
  <div id="app">
    <div>403</div>
    <div class="txt"> Forbidden<span class="blink">_</span> </div>
  </div>
</body>
</html> '''

# ========== App Data ==========

stored_links = {}
_TEMP_SONGS = {}

# ========== Helper Functions ==========

def get_palette(cover_url):
    """Return dominant color and a palette of 3 colors as hex strings"""
    try:
        resp = requests.get(cover_url, timeout=6)
        img_bytes = io.BytesIO(resp.content)
        thief = ColorThief(img_bytes)
        dom = thief.get_color(quality=2)
        pal = thief.get_palette(color_count=3)
        tohex = lambda rgb: '#%02x%02x%02x' % rgb
        # Slightly darken if mostly white to improve contrast
        darken_if_light = lambda c: tuple(int(x*0.82) if sum(c)//3 > 210 else x for x in c)
        dom = darken_if_light(dom)
        pal = [darken_if_light(color) for color in pal]
        dom_hex = tohex(dom)
        pal_hex = [tohex(c) for c in pal]
        return dom_hex, pal_hex
    except Exception as e:
        print("Palette extraction failed:", e)
        # Return warm fallback palette
        return "#ff6600", ["#ffa84f", "#bf482d", "#ffbb7b"]

def fetch(query, retries=10, delay=2):
    url = f"https://api-v2.soundcloud.com/search/tracks?q={query}&client_id={CLIENT_ID}&limit=6"
    for attempt in range(1, retries + 1):
        try:
            res = requests.get(url)
            if res.status_code == 200:
                data = res.json()
                tracks = []
                links = []
                for idx, track in enumerate(data.get("collection", []), start=1):
                    cover = (track.get('artwork_url') or track.get('user', {}).get('avatar_url', None))
                    if cover:
                        cover = cover.replace('large','t500x500').replace('-t50x50', '-t500x500')
                        dom, pal = get_palette(cover)
                    else:
                        dom, pal = "#ff6600", ["#ffa84f", "#bf482d", "#ffbb7b"]
                    tracks.append({
                        'no': idx,
                        'title': track['title'],
                        'artist': track['user']['username'],
                        'url': track['permalink_url'],
                        'cover': cover,
                        'dom': dom,
                        'pal': pal,
                    })
                    links.append(track['permalink_url'])
                return tracks, links
        except Exception as e:
            print(f"[Attempt {attempt}] Error: {e}")
        print(f"[Attempt {attempt}] Retrying in {delay} sec... (status: {getattr(res,'status_code', None)})")
        time.sleep(delay)
    return None, "Failed after retries"

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
            song_data = f.read()
            return (song_data, os.path.basename(filepath)), "✅ Stream ready"

def fetch_lyrics_genius(song):
    global song_name
    song_title = song_name
    print('Getting lyrics for:', song_name)
    try:
        song = genius.search_song(song_title)
        if song and song.lyrics:
            lyrics = song.lyrics
            if "*******" in lyrics:
                lyrics = lyrics.split("*******")[0].strip()
            elif "Embed" in lyrics:
                lyrics = lyrics.split("Embed")[0].strip()
            return lyrics
        return None
    except Exception as e:
        print(f"Error fetching lyrics via Genius: {e}")
        return None

# ========== Flask Routes ==========

@app.route("/")
def index():
    return INDEX_HTML

@app.route("/search", methods=["POST"])
def search():
    global song_name
    query = request.form.get("song_name", "").strip()
    song_name = query
    if not query:
        return render_template_string(SEARCH_RESULTS_HTML, query=query, tracks=[], error="Please enter a song name.")
    tracks, links_or_error = fetch(query)
    if tracks is None:
        if "404" in links_or_error or "403" in links_or_error:
            return FORBIDDEN_HTML
        return render_template_string(SEARCH_RESULTS_HTML, query=query, tracks=[], error=links_or_error)
    stored_links[query] = {'links': links_or_error, 'tracks': tracks}
    return render_template_string(SEARCH_RESULTS_HTML, query=query, tracks=tracks, error=None)

@app.route("/stream", methods=["POST"])
def stream():
    query = request.form.get("query", "")
    song_no_action = request.form.get("song_no", "")
    if "|" in song_no_action:
        song_no, action = song_no_action.split("|", 1)
    else:
        return "⚠️ Invalid selection."
    if query not in stored_links:
        return "⚠️ Session expired or invalid query."
    tracklist = stored_links[query]['tracks']
    try:
        song_idx = int(song_no) - 1
        link = stored_links[query]['links'][song_idx]
        this_track = tracklist[song_idx]
        cover = this_track.get('cover')
    except Exception:
        return "⚠️ Invalid selection."
    result, msg = download_song_to_memory(link)
    if not result:
        return f"❌ Error:\n{msg}", 500
    song_data, filename = result
    ext = filename.lower()
    MIME = (
        "audio/mpeg" if ext.endswith('.mp3') else
        "audio/x-m4a" if ext.endswith('.m4a') else
        "audio/flac" if ext.endswith('.flac') else
        "audio/wav" if ext.endswith('.wav') else
        "application/octet-stream"
    )
    song_id = f"{query}-{song_no}"
    dominant_color = get_palette(cover)[0] if cover else "#ff6600"
    if action == "listen":
        _TEMP_SONGS[song_id] = (song_data, filename, MIME)
        lyrics = fetch_lyrics_genius(this_track['title'])
        return render_template_string(
            PLAYER_HTML,
            song_id=song_id,
            filename=filename,
            MIME=MIME,
            cover=cover,
            lyrics=lyrics,
            dominant_color=dominant_color
        )
    else:
        song_bytes = io.BytesIO(song_data)
        return send_file(song_bytes, as_attachment=True, download_name=filename)

@app.route("/media/<song_id>")
def media(song_id):
    item = _TEMP_SONGS.get(song_id)
    if not item:
        return "Session expired or unavailable", 410
    song_data, filename, MIME = item
    song_bytes = io.BytesIO(song_data)
    if request.args.get('download'):
        return send_file(song_bytes, download_name=filename, as_attachment=True)
    return send_file(song_bytes, mimetype=MIME, as_attachment=False, download_name=filename)

if __name__ == "__main__":
    app.run(debug=True)
