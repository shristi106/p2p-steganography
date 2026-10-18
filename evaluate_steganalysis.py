
import csv
import json
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


COVER = Path("test_files/cover.png")
SAMPLE = Path("test_files/sample.txt")
OUTPUT_DIR = Path("test_files/steganalysis")
CSV_PATH = Path("steganalysis_results.csv")

TRIALS = 3
PADDING_SIZES = [0, 128, 512]


def image_statistics(cover_path, stego_path):
    with Image.open(cover_path) as im:
        cover = np.asarray(im.convert("RGB"), dtype=np.uint8)

    with Image.open(stego_path) as im:
        stego = np.asarray(im.convert("RGB"), dtype=np.uint8)

    if cover.shape != stego.shape:
        raise ValueError("Cover and stego image dimensions differ.")

    cover_lsb = (cover & 1).astype(np.float64)
    stego_lsb = (stego & 1).astype(np.float64)

    def adjacent_correlation(bits):
        # Correlation between horizontally adjacent red-channel LSBs.
        red = bits[:, :, 0]
        left = red[:, :-1].ravel()
        right = red[:, 1:].ravel()

        if len(left) < 2 or np.std(left) == 0 or np.std(right) == 0:
            return 0.0

        return float(np.corrcoef(left, right)[0, 1])

    mse = float(mean_squared_error(cover, stego))
    psnr = float(
        peak_signal_noise_ratio(cover, stego, data_range=255)
    )
    ssim = float(
        structural_similarity(
            cover, stego, channel_axis=2, data_range=255
        )
    )

    return {
        "mse": mse,
        "psnr_db": psnr,
        "ssim": ssim,
        "cover_lsb_one_fraction": float(np.mean(cover_lsb)),
        "stego_lsb_one_fraction": float(np.mean(stego_lsb)),
        "lsb_one_fraction_change": float(
            abs(np.mean(stego_lsb) - np.mean(cover_lsb))
        ),
        "cover_red_lsb_adjacent_correlation":
            adjacent_correlation(cover_lsb),
        "stego_red_lsb_adjacent_correlation":
            adjacent_correlation(stego_lsb),
    }


def main():
    if not COVER.is_file():
        raise FileNotFoundError(f"Missing cover image: {COVER}")

    if not SAMPLE.is_file():
        raise FileNotFoundError(f"Missing sample file: {SAMPLE}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    base_metadata = {
        "file_name": SAMPLE.name,
        "sha256": calculate_sha256(str(SAMPLE)),
        "peer_id": "peer_001",
    }

    rows = []

    for padding_size in PADDING_SIZES:
        metadata = dict(base_metadata)
        metadata["padding"] = "X" * padding_size
        message = json.dumps(metadata, separators=(",", ":"))

        print(f"\nPayload size: {len(message.encode('utf-8'))} bytes")

        for method in ("Fixed-order LSB", "Adaptive LSB"):
            for trial in range(1, TRIALS + 1):
                output_path = OUTPUT_DIR / (
                    f"{method.split()[0].lower()}_"
                    f"pad{padding_size}_trial{trial}.png"
                )

                start = time.perf_counter()

                if method == "Fixed-order LSB":
                    embed_message(
                        str(COVER), str(output_path), message
                    )
                else:
                    embed_adaptive_message(
                        COVER, output_path, message
                    )

                embedding_ms = (
                    time.perf_counter() - start
                ) * 1000

                start = time.perf_counter()

                if method == "Fixed-order LSB":
                    extracted = extract_message(str(output_path))
                else:
                    extracted = extract_adaptive_message(output_path)

                extraction_ms = (
                    time.perf_counter() - start
                ) * 1000

                extraction_success = extracted == message

                metrics = image_statistics(COVER, output_path)

                row = {
                    "method": method,
                    "padding_bytes": padding_size,
                    "payload_bytes": len(message.encode("utf-8")),
                    "trial": trial,
                    "embedding_time_ms": embedding_ms,
                    "extraction_time_ms": extraction_ms,
                    "extraction_success": extraction_success,
                    **metrics,
                }

                rows.append(row)

                print(
                    f"{method}, trial {trial}: "
                    f"extraction={extraction_success}, "
                    f"embed={embedding_ms:.2f} ms, "
                    f"extract={extraction_ms:.2f} ms"
                )

    if not all(row["extraction_success"] for row in rows):
        raise RuntimeError(
            "At least one extraction failed. Inspect the output "
            "before using these results."
        )

    with CSV_PATH.open(
        "w", newline="", encoding="utf-8"
    ) as file:
        writer = csv.DictWriter(
            file, fieldnames=list(rows[0].keys())
        )
        writer.writeheader()
        writer.writerows(rows)

    print("\n========== EVALUATION COMPLETE ==========")
    print(f"Configurations: {len(PADDING_SIZES)} payload sizes")
    print(f"Trials per method and payload: {TRIALS}")
    print(f"Total successful runs: {len(rows)}")
    print(f"Results saved to: {CSV_PATH}")
    print("\nRemember: these statistics do not prove resistance")
    print("to steganalysis. The experiment uses one cover image.")


if __name__ == "__main__":
    main()
