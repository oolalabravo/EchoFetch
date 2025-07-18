
# 🎵 Spotify Downloader

A modern, responsive, and animated Spotify downloader web application built using **Flask**, **Spotipy**, **Tailwind CSS**, and **GSAP**. It allows users to search for and download songs from Spotify using the track URL or ID.  

> 🔐 Powered by Spotify’s public API using `spotipy`  
> ✨ Stylish interface with `GSAP` animations and `Tailwind CSS`  
> ⚡ Super-fast Flask backend  
> 📥 Local download directory handling  

---

## 📸 Preview

[![Website Preview](./preview.png)](https://echofetch-production.up.railway.app/)
*Simple, clean, and elegant interface*
Hosted on Railway 
---

## 🚀 Features

- ✅ Spotify API search support  
- ✅ Auto-download song using ID or full URL  
- ✅ Animated UI with GSAP  
- ✅ Mobile-first responsive layout  
- ✅ Flask-based log output system  
- ✅ Error feedback for invalid secrets or requests

---

## 🛠️ Tech Stack

| Tech       | Usage                          |
|------------|--------------------------------|
| Flask      | Backend Python web server      |
| Spotipy    | Spotify Web API (client auth)  |
| GSAP       | Smooth frontend animations     |
| TailwindCSS| Frontend styling framework     |
| HTML/JS    | User interaction + layout      |

---

## 🔐 Setup & Installation

### 1. Clone the repository

```bash
git clone https://github.com/oolalabravo/EchoFetch.git
cd spotify-downloader
````

### 2. Install requirements

```bash
pip install -r requirements.txt
```

### 3. Add your Spotify credentials

Create a `.env` file or pass the secrets as GitHub Secrets or environment variables:

```
SPOTIPY_CLIENT_ID=your_client_id
SPOTIPY_CLIENT_SECRET=your_client_secret
```

> ⚠️ Don't forget: client secrets **must NOT** be inside quotes in `.env` files or GitHub secrets, treat them like passwords and keep safe.

---

## 🔧 Running the app

```bash
python app.py
```

Visit `http://127.0.0.1:5000` in your browser.
You should see your Spotify downloader UI with GSAP-powered transitions.

---

## 🪲 Troubleshooting

| Issue                   | Solution                                             |
| ----------------------- | ---------------------------------------------------- |
| `invalid_client`        | Check if your client secret is valid & not in quotes |
| Songs not downloading   | Ensure stable internet connection                 |
| UI not loading properly | Check console for GSAP/CDN errors                    |

---

## 🏷️ Tags

`spotify` `downloader` `flask` `python` `tailwind` `gsap` `webapp` `music` `spotipy` `animation` `open-source`

---

## 📄 License

This project is licensed under the [MIT License](./LICENSE).

---

## 🙌 Acknowledgments

* [Spotipy Docs](https://spotipy.readthedocs.io/)
* [GSAP Animations](https://greensock.com/gsap/)
* [TailwindCSS](https://tailwindcss.com/)

---

> Made with ❤️ by \[Bhvaya sharma]

```

---

Let me know if you want:
- A `LICENSE` file (I’ll generate it for MIT).
- Markdown badges (build, license, etc.).
- Auto-deploy GitHub Actions workflow file.
- Custom preview image setup.
```
