from __future__ import annotations

import csv
import secrets
import time
from pathlib import Path
from uuid import uuid4

from flask import Flask, jsonify, render_template, request, send_from_directory, url_for
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.utils import secure_filename
from PIL import Image

from steganography import embed_message, extract_message
from adaptive_steganography import embed_adaptive_message, extract_adaptive_message
from integrity import calculate_sha256, verify_integrity

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(__import__("os").environ.get("VEILLINK_DATA_DIR", str(BASE_DIR / "instance")))
UPLOAD_DIR = DATA_DIR / "uploads"
OUTPUT_DIR = DATA_DIR / "generated"
RELAY_DIR = DATA_DIR / "relay"
for folder in (UPLOAD_DIR, OUTPUT_DIR, RELAY_DIR):
    folder.mkdir(parents=True, exist_ok=True)

ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "bmp"}
MAX_UPLOAD_BYTES = 12 * 1024 * 1024
RELAY_TTL_SECONDS = 30 * 60
# In-memory relay metadata is intentionally short-lived. A restart clears share codes.
RELAYS: dict[str, dict] = {}

app = Flask(__name__)
# Render sits behind one trusted reverse proxy; preserve HTTPS when building share URLs.
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_BYTES


def json_error(message: str, status: int = 400):
    return jsonify({"ok": False, "error": message}), status


def save_upload(file_storage, target_dir: Path, allowed_extensions=None) -> Path:
    if not file_storage or not file_storage.filename:
        raise ValueError("Choose a file first.")
    original_name = secure_filename(file_storage.filename)
    if not original_name:
        raise ValueError("The uploaded filename is invalid.")
    if allowed_extensions is not None:
        extension = original_name.rsplit(".", 1)[-1].lower() if "." in original_name else ""
        if extension not in allowed_extensions:
            raise ValueError("Unsupported file type. Upload a PNG, JPG, JPEG, WEBP, or BMP image.")
    target = target_dir / f"{uuid4().hex}_{original_name}"
    file_storage.save(target)
    if target.stat().st_size == 0:
        target.unlink(missing_ok=True)
        raise ValueError("The uploaded file is empty.")
    return target


def validate_image(path: Path) -> None:
    try:
        with Image.open(path) as image:
            image.verify()
    except Exception as exc:
        path.unlink(missing_ok=True)
        raise ValueError("That file does not appear to be a valid image.") from exc


def clean_expired_relays() -> None:
    now = time.time()
    expired = [code for code, entry in RELAYS.items() if entry["expires_at"] < now]
    for code in expired:
        entry = RELAYS.pop(code, None)
        if entry:
            Path(entry["path"]).unlink(missing_ok=True)


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/health")
def health():
    return jsonify({"ok": True, "service": "VeilLink"})


@app.post("/api/embed")
def api_embed():
    source = None
    output = None
    try:
        source = save_upload(request.files.get("image"), UPLOAD_DIR, ALLOWED_IMAGE_EXTENSIONS)
        validate_image(source)
        message = request.form.get("message", "")
        if not message.strip():
            raise ValueError("Enter a message to hide.")
        if len(message.encode("utf-8")) > 100_000:
            raise ValueError("The message is too large. Keep it under 100 KB.")
        algorithm = request.form.get("algorithm", "fixed")
        output = OUTPUT_DIR / f"veilink_{uuid4().hex}.png"
        if algorithm == "adaptive":
            embed_adaptive_message(str(source), str(output), message)
            algorithm_label = "Adaptive LSB"
        elif algorithm == "fixed":
            embed_message(str(source), str(output), message)
            algorithm_label = "Fixed-order LSB"
        else:
            raise ValueError("Choose a supported embedding algorithm.")
        return jsonify({
            "ok": True,
            "message": "Message embedded successfully.",
            "algorithm": algorithm_label,
            "filename": output.name,
            "download_url": url_for("download_generated", filename=output.name),
            "sha256": calculate_sha256(str(output)),
            "bytes": output.stat().st_size,
        })
    except (ValueError, OSError, UnicodeDecodeError) as exc:
        if output:
            output.unlink(missing_ok=True)
        return json_error(str(exc))
    finally:
        if source:
            source.unlink(missing_ok=True)


@app.post("/api/extract")
def api_extract():
    source = None
    try:
        source = save_upload(request.files.get("image"), UPLOAD_DIR, ALLOWED_IMAGE_EXTENSIONS)
        validate_image(source)
        algorithm = request.form.get("algorithm", "fixed")
        if algorithm == "adaptive":
            message = extract_adaptive_message(str(source))
            algorithm_label = "Adaptive LSB"
        elif algorithm == "fixed":
            message = extract_message(str(source))
            algorithm_label = "Fixed-order LSB"
        else:
            raise ValueError("Choose a supported extraction algorithm.")
        return jsonify({"ok": True, "message": message, "algorithm": algorithm_label})
    except (ValueError, OSError, UnicodeDecodeError) as exc:
        return json_error(str(exc))
    finally:
        if source:
            source.unlink(missing_ok=True)


@app.post("/api/verify")
def api_verify():
    original = received = None
    try:
        original = save_upload(request.files.get("original"), UPLOAD_DIR)
        received = save_upload(request.files.get("received"), UPLOAD_DIR)
        original_hash = calculate_sha256(str(original))
        received_hash = calculate_sha256(str(received))
        matched = verify_integrity(original_hash, received_hash)
        return jsonify({
            "ok": True,
            "match": matched,
            "status": "MATCH" if matched else "MISMATCH",
            "original_sha256": original_hash,
            "received_sha256": received_hash,
            "message": "The files are byte-for-byte identical." if matched else "The files differ. At least one byte has changed.",
            "note": "A matching SHA-256 hash checks file integrity; it does not prove who sent the file.",
        })
    except (ValueError, OSError) as exc:
        return json_error(str(exc))
    finally:
        for path in (original, received):
            if path:
                path.unlink(missing_ok=True)


@app.post("/api/relay")
def api_relay():
    source = None
    try:
        clean_expired_relays()
        source = save_upload(request.files.get("file"), RELAY_DIR, ALLOWED_IMAGE_EXTENSIONS)
        validate_image(source)
        code = secrets.token_hex(4)
        # Store a safe display name separately from the random storage path.
        display_name = secure_filename(request.files["file"].filename) or "shared-image.png"
        RELAYS[code] = {
            "path": str(source),
            "filename": display_name,
            "expires_at": time.time() + RELAY_TTL_SECONDS,
        }
        source = None  # Relay owns the file until expiry/download.
        return jsonify({
            "ok": True,
            "code": code,
            "filename": display_name,
            "download_url": url_for("relay_download", code=code, _external=True),
            "expires_in_minutes": 30,
            "message": "Relay link created. Anyone with the link can download this file until it expires.",
        })
    except (ValueError, OSError) as exc:
        return json_error(str(exc))
    finally:
        if source:
            source.unlink(missing_ok=True)


@app.get("/relay/<code>")
def relay_download(code: str):
    clean_expired_relays()
    entry = RELAYS.get(code)
    if not entry or entry["expires_at"] < time.time():
        RELAYS.pop(code, None)
        return render_template("index.html", expired_code=True), 404
    return send_from_directory(RELAY_DIR, Path(entry["path"]).name, as_attachment=True, download_name=entry["filename"])


@app.get("/files/<path:filename>")
def download_generated(filename: str):
    return send_from_directory(OUTPUT_DIR, filename, as_attachment=True)


@app.get("/api/metrics")
def api_metrics():
    path = BASE_DIR / "evaluation_results.csv"
    if not path.exists():
        return jsonify({"ok": True, "available": False, "message": "No evaluation_results.csv file was found."})
    try:
        with path.open("r", newline="", encoding="utf-8-sig") as handle:
            rows = list(csv.DictReader(handle))
        if not rows:
            return jsonify({"ok": True, "available": False, "message": "The evaluation file has no data rows."})
        latest = rows[-1]
        return jsonify({"ok": True, "available": True, "sample_count": len(rows), "sample": latest})
    except OSError as exc:
        return json_error(f"Could not read evaluation data: {exc}", 500)


@app.errorhandler(413)
def too_large(_error):
    return json_error("Upload too large. The maximum file size is 12 MB.", 413)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(__import__("os").environ.get("PORT", "5000")), debug=False)
