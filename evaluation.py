
import csv
import json
import time
from pathlib import Path

import numpy as np
from PIL import Image
from skimage.metrics import structural_similarity

from integrity import calculate_sha256
from steganography import embed_message, extract_message


def evaluate_project():
    """Evaluate steganography, image quality, and received-file integrity."""

    original_file = Path("test_files/sample.txt")
    cover_image = Path("test_files/cover.png")
    stego_image = Path("test_files/evaluation_stego.png")

    received_file = Path("received_files/sample.txt")
    received_stego = Path("received_files/stego_image.png")

    # Check that the input files exist.
    if not original_file.exists():
        raise FileNotFoundError(f"Missing file: {original_file}")

    if not cover_image.exists():
        raise FileNotFoundError(f"Missing file: {cover_image}")

    # 1. Measure SHA-256 calculation time.
    start = time.perf_counter()
    original_hash = calculate_sha256(str(original_file))
    hash_time = time.perf_counter() - start

    # 2. Prepare and embed metadata.
    metadata = {
        "file_name": original_file.name,
        "sha256": original_hash,
        "peer_id": "peer_001",
    }

    message = json.dumps(metadata)

    start = time.perf_counter()
    embed_message(str(cover_image), str(stego_image), message)
    embedding_time = time.perf_counter() - start

    # 3. Extract metadata and measure extraction time.
    start = time.perf_counter()
    extracted_message = extract_message(str(stego_image))
    extraction_time = time.perf_counter() - start

    extraction_success = extracted_message == message

    # 4. Calculate image quality metrics.
    cover = np.asarray(
        Image.open(cover_image).convert("RGB"),
        dtype=np.float64,
    )

    stego = np.asarray(
        Image.open(stego_image).convert("RGB"),
        dtype=np.float64,
    )

    mse = float(np.mean((cover - stego) ** 2))

    if mse == 0:
        psnr = float("inf")
    else:
        psnr = float(10 * np.log10((255 ** 2) / mse))

    ssim = float(
        structural_similarity(
            cover,
            stego,
            channel_axis=2,
            data_range=255,
        )
    )

    # 5. Verify the file actually received over TCP.
    if not received_file.exists() or not received_stego.exists():
        raise FileNotFoundError(
            "Received files are missing. First run prepare_transfer.py, "
            "then run receiver.py and send the files using network.py."
        )

    start = time.perf_counter()

    received_metadata = json.loads(
        extract_message(str(received_stego))
    )

    embedded_hash = received_metadata["sha256"]
    received_hash = calculate_sha256(str(received_file))

    integrity_time = time.perf_counter() - start
    integrity_passed = embedded_hash == received_hash

    # 6. Store the measurements.
    results = {
        "file_size_bytes": original_file.stat().st_size,
        "hash_time_ms": hash_time * 1000,
        "embedding_time_ms": embedding_time * 1000,
        "extraction_time_ms": extraction_time * 1000,
        "integrity_check_time_ms": integrity_time * 1000,
        "extraction_success": extraction_success,
        "integrity_passed": integrity_passed,
        "embedded_hash": embedded_hash,
        "received_hash": received_hash,
        "mse": mse,
        "psnr_db": psnr,
        "ssim": ssim,
    }

    print("\n========== PERFORMANCE EVALUATION ==========")

    for metric, value in results.items():
        print(f"{metric}: {value}")

    # 7. Save results to CSV.
    output_file = Path("evaluation_results.csv")

    with output_file.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=results.keys(),
        )
        writer.writeheader()
        writer.writerow(results)

    print(f"\nResults saved to: {output_file}")


if __name__ == "__main__":
    try:
        evaluate_project()
    except (
        OSError,
        ValueError,
        KeyError,
        json.JSONDecodeError,
    ) as error:
        print("Evaluation error:", error)
