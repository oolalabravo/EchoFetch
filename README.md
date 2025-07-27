

# 🎵 SoundCloud Downloader -EcoFetch

A sleek, minimal Flask web application to search and download top tracks from SoundCloud using a client ID and `scdl`. Supports streaming 3 top search results and downloading the selected song directly to your device.


---

## 🚀 Features

* 🔍 Search any song on SoundCloud.
* 🎶 Displays top 3 matching tracks with artist names.
* 📥 Download selected song directly from browser.
* 🎨 Clean, modern, responsive UI using HTML + CSS.
* ⚙️ Backend powered by Flask and SoundCloud API v2.
* 🐚 Uses `scdl` CLI to download the song locally in memory.

---

## 🛠️ Requirements

Make sure you have the following installed:

* Python 3.7+
* pip
* `scdl` (SoundCloud downloader CLI tool)
* `ffmpeg` (for some formats)
* A valid SoundCloud **Client ID**

---

## 📦 Installation

### 1. Clone the repository

```bash
git clone https://github.com/oolalabravo/EcoFetch.git
cd soundcloud-downloader-flask
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

---

## 🔐 Environment Setup

### Set your SoundCloud Client ID

This app uses the SoundCloud API v2, which requires a `client_id`.

#### 1. Get your Client ID:

* Visit [https://soundcloud.com/](https://soundcloud.com/)
* Log in → Open browser dev tools → Network tab → Search something.
* Look for a request to `api-v2.soundcloud.com` and find `client_id=...`.

#### 2. Set it in the code:

In your Python file (top of the script), replace:

```python
CLIENT_ID = "CLIENT_ID"
```

with:

```python
CLIENT_ID = "your_actual_client_id"
```

> Alternatively, store it in an `.env` file and read with `python-dotenv`.

---

## ▶️ Run the App

```bash
python app.py
```

Or if running in a Railway/Heroku environment:

```bash
PORT=5000 python app.py
```

Now open your browser and go to:

```
http://127.0.0.1:5000
```

---

## 🖼️ Usage

1. Enter the name of a song in the input box.
2. View the top 3 results with artist names.
3. Select one and click **"Stream Selected Song"**.
4. Your song will be streamed and downloaded instantly.

---

## 🌐 Deployment Tips

To deploy this app to **Railway**, **Heroku**, or **Render**:

* Make sure `scdl` is available in build commands.
* Set `PORT` environment variable.
* If needed, make a `Procfile` with:

```
web: python app.py
```

* Set the `CLIENT_ID` as an environment variable or hardcode it if deploying privately.

---

## 🔍 Troubleshooting

| Issue                 | Solution                                                                       |
| --------------------- | ------------------------------------------------------------------------------ |
| `scdl not found`      | Ensure it’s installed and added to PATH. Try `pip install scdl` again.         |
| `No audio file found` | The track may not be downloadable or available in supported formats.           |
| `403 Forbidden`       | Your client ID might be invalid or rate-limited. Rotate it or fetch a new one. |

---

## 📁 File Structure

```
├── app.py                # Main Flask app
├── templates             # (HTML is rendered as string inline)
├── static                # Where scdl saves downloaded songs temporarily
├── requirements.txt      # Dependencies (Flask, requests)
```

---

## 💡 Future Ideas

* Add support for downloading playlists.
* Use JavaScript frontend and API backend.
* Add multiple quality/resolution options.
* Deploy using Docker or fly.io for portability.

---

## ❤️ Credits

* UI inspired by [Inter Font](https://rsms.me/inter/)
* Powered by [SoundCloud API](https://developers.soundcloud.com/docs/api/guide)
* Backend by Flask & `scdl` CLI

---

## 📜 License

This project is open-source and licensed under the [MIT License](LICENSE).

---

