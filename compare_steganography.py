
import csv
import time
from pathlib import Path

import numpy as np
from PIL import Image
from skimage.metrics import (
    mean_squared_error,
    peak_signal_noise_ratio,
    structural_similarity,
)

from integrity import calculate_sha256
from steganography import embed_message, extract_message
from adaptive_steganography import (
    embed_adaptive_message,
    extract_adaptive_message,
)


COVER_IMAGE = Path("test_files/cover.png")
ORIGINAL_FILE = Path("test_files/sample.txt")
FIXED_IMAGE = Path("test_files/fixed_comparison.png")
ADAPTIVE_IMAGE = Path("test_files/adaptive_comparison.png")
RESULTS_FILE = Path("steganography_comparison.csv")


def image_metrics(cover_path, stego_path):
    with Image.open(cover_path) as image:
        cover = np.asarray(image.convert("RGB"), dtype=np.uint8)

    with Image.open(stego_path) as image:
        stego = np.asarray(image.convert("RGB"), dtype=np.uint8)

    if cover.shape != stego.shape:
        raise ValueError("Cover and stego images have different dimensions.")

    mse = mean_squared_error(cover, stego)
    psnr = peak_signal_noise_ratio(cover, stego, data_range=255)
    ssim = structural_similarity(
        cover,
        stego,
        channel_axis=2,
        data_range=255,
    )

    # Compare the frequency of zero and one values in RGB LSBs.
    cover_lsb = cover & 1
    stego_lsb = stego & 1

    cover_ones = float(np.mean(cover_lsb))
    stego_ones = float(np.mean(stego_lsb))

    lsb_distribution_change = abs(stego_ones - cover_ones)

    return {
        "mse": float(mse),
        "psnr_db": float(psnr),
        "ssim": float(ssim),
        "cover_lsb_one_fraction": cover_ones,
        "stego_lsb_one_fraction": stego_ones,
        "lsb_one_fraction_change": lsb_distribution_change,
    }


def main():
    if not COVER_IMAGE.is_file():
        raise FileNotFoundError(f"Missing cover image: {COVER_IMAGE}")

    if not ORIGINAL_FILE.is_file():
        raise FileNotFoundError(f"Missing sample file: {ORIGINAL_FILE}")

    # Use the same payload for both methods.
    metadata = (
        '{"file_name":"sample.txt",'
        '"sha256":"' + calculate_sha256(str(ORIGINAL_FILE)) + '",'
        '"peer_id":"peer_001"}'
    )

    print("Embedding with fixed-order LSB...")
    start = time.perf_counter()
    embed_message(str(COVER_IMAGE), str(FIXED_IMAGE), metadata)
    fixed_embedding_ms = (time.perf_counter() - start) * 1000

    print("\nEmbedding with adaptive LSB...")
    start = time.perf_counter()
    embed_adaptive_message(COVER_IMAGE, ADAPTIVE_IMAGE, metadata)
    adaptive_embedding_ms = (time.perf_counter() - start) * 1000

    print("\nExtracting and checking messages...")
    fixed_start = time.perf_counter()
    fixed_message = extract_message(str(FIXED_IMAGE))
    fixed_extraction_ms = (time.perf_counter() - fixed_start) * 1000

    adaptive_start = time.perf_counter()
    adaptive_message = extract_adaptive_message(ADAPTIVE_IMAGE)
    adaptive_extraction_ms = (
        time.perf_counter() - adaptive_start
    ) * 1000

    fixed_success = fixed_message == metadata
    adaptive_success = adaptive_message == metadata

    results = []

    for method, image_path, embed_ms, extract_ms, success in [
        (
            "Fixed-order LSB",
            FIXED_IMAGE,
            fixed_embedding_ms,
            fixed_extraction_ms,
            fixed_success,
        ),
        (
            "Adaptive LSB",
            ADAPTIVE_IMAGE,
            adaptive_embedding_ms,
            adaptive_extraction_ms,
            adaptive_success,
        ),
    ]:
        metrics = image_metrics(COVER_IMAGE, image_path)

        row = {
            "method": method,
            "embedding_time_ms": embed_ms,
            "extraction_time_ms": extract_ms,
            "extraction_success": success,
            **metrics,
        }

        results.append(row)

    print("\n========== STEGANOGRAPHY COMPARISON ==========")

    for row in results:
        print(f"\nMethod: {row['method']}")
        for key, value in row.items():
            if key != "method":
                print(f"{key}: {value}")

    with RESULTS_FILE.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=list(results[0].keys()),
        )
        writer.writeheader()
        writer.writerows(results)

    print(f"\nResults saved to: {RESULTS_FILE}")

    if not fixed_success or not adaptive_success:
        raise RuntimeError(
            "At least one method failed extraction. "
            "Do not use this comparison as a successful result."
        )


if __name__ == "__main__":
    main()
