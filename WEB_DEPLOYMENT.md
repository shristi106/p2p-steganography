# VeilLink web integration patch

This patch adds a Flask interface to the existing P2P steganography repository. It expects these existing project files to remain in the repository root:

- `steganography.py`
- `adaptive_steganography.py`
- `integrity.py`
- `evaluation_results.csv` (optional, used by Research Metrics)

## Features

- Dark cybersecurity UI with neon-green accents
- Fixed-order and adaptive LSB embed/extract using the existing project functions
- SHA-256 comparison of two uploaded files
- Temporary image relay links that expire after 30 minutes
- Research Metrics panel reading the existing CSV
- Flask health endpoint at `/health`

## Run locally (Windows PowerShell)

Copy the files from this patch into the repository root, preserving the `templates` and `static` folders. Then run:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```

Open `http://127.0.0.1:5000`.

## Deploy on Render

1. Add these files to the root of `shristi106/p2p-steganography` and push them to GitHub.
2. In Render, choose **New + → Blueprint** and select the repository. Render reads `render.yaml`.
3. Wait for the build to complete, then open the Render URL and check `/health` returns `{"ok": true, "service": "VeilLink"}`.

Alternatively create a Web Service with build command `pip install -r requirements.txt` and start command `gunicorn app:app --workers 2 --threads 4 --timeout 60`.

## Important limitations

- This is a web relay, not direct device-to-device TCP. The repository's original `network.py` binds to `127.0.0.1`; that local socket is not a public internet endpoint.
- Relay metadata is in memory and the uploaded relay file is on the service's local filesystem. A restart or redeploy clears active links; this is suitable for a demo, not reliable long-term storage.
- Anyone with a relay URL can download that file before it expires. Do not upload confidential material to an unauthenticated public deployment.
- LSB embedding is not encryption. SHA-256 comparison detects byte differences but does not authenticate the sender.
- The web interface accepts uploads up to 12 MB and restricts embedding/extraction/relay uploads to common image formats. For production use, add authentication, rate limiting, persistent storage, malware scanning, and stronger operational controls.
