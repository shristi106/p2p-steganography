
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


COVERS_DIR = Path("test_files/covers_png")
SAMPLE_FILE = Path("test_files/sample.txt")
OUTPUT_DIR = Path("test_files/multi_cover_results")
CSV_PATH = Path("multi_cover_evaluation.csv")

TRIALS = 3
PADDING_SIZES = [0, 128, 512]


def calculate_metrics(cover_path, stego_path):
    with Image.open(cover_path) as image:
        cover = np.asarray(image.convert("RGB"), dtype=np.uint8)

    with Image.open(stego_path) as image:
        stego = np.asarray(image.convert("RGB"), dtype=np.uint8)

    if cover.shape != stego.shape:
        raise ValueError("Cover and stego dimensions do not match.")

    cover_lsb = (cover & 1).astype(np.float64)
    stego_lsb = (stego & 1).astype(np.float64)

    # Horizontal adjacent correlation for red-channel LSBs.
    def red_lsb_correlation(bits):
        red = bits[:, :, 0]
        left = red[:, :-1].ravel()
        right = red[:, 1:].ravel()

        if (
            len(left) < 2
            or np.std(left) == 0
            or np.std(right) == 0
        ):
            return 0.0

        return float(np.corrcoef(left, right)[0, 1])

    return {
        "mse": float(mean_squared_error(cover, stego)),
        "psnr_db": float(
            peak_signal_noise_ratio(cover, stego, data_range=255)
        ),
        "ssim": float(
            structural_similarity(
                cover, stego, channel_axis=2, data_range=255
            )
        ),
        "cover_lsb_one_fraction": float(np.mean(cover_lsb)),
        "stego_lsb_one_fraction": float(np.mean(stego_lsb)),
        "lsb_one_fraction_change": float(
            abs(np.mean(stego_lsb) - np.mean(cover_lsb))
        ),
        "cover_red_lsb_correlation": red_lsb_correlation(cover_lsb),
        "stego_red_lsb_correlation": red_lsb_correlation(stego_lsb),
    }


def main():
    if not SAMPLE_FILE.is_file():
        raise FileNotFoundError(f"Missing sample file: {SAMPLE_FILE}")

    if not COVERS_DIR.is_dir():
        raise FileNotFoundError(f"Missing covers directory: {COVERS_DIR}")

    covers = sorted(COVERS_DIR.glob("*.png"))

    if len(covers) < 3:
        raise ValueError(
            f"Expected at least three PNG covers in {COVERS_DIR}; "
            f"found {len(covers)}."
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    original_hash = calculate_sha256(str(SAMPLE_FILE))
    rows = []

    for cover_path in covers:
        print(f"\n========== COVER: {cover_path.name} ==========")

        for padding_size in PADDING_SIZES:
            padding = "X" * padding_size

            # Same payload for both methods on this cover and size.
            message = (
                '{"file_name":"sample.txt",'
                f'"sha256":"{original_hash}",'
                '"peer_id":"peer_001",'
                f'"padding":"{padding}"'
                '}'
            )

            for method in ("Fixed-order LSB", "Adaptive LSB"):
                for trial in range(1, TRIALS + 1):
                    stem = (
                        f"{cover_path.stem}_pad{padding_size}_"
                        f"{method.split()[0].lower()}_trial{trial}"
                    )
                    output_path = OUTPUT_DIR / f"{stem}.png"

                    start = time.perf_counter()

                    if method == "Fixed-order LSB":
                        embed_message(
                            str(cover_path), str(output_path), message
                        )
                    else:
                        embed_adaptive_message(
                            cover_path, output_path, message
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

                    success = extracted == message
                    metrics = calculate_metrics(cover_path, output_path)

                    row = {
                        "cover": cover_path.name,
                        "method": method,
                        "padding_bytes": padding_size,
                        "payload_bytes": len(message.encode("utf-8")),
                        "trial": trial,
                        "embedding_time_ms": embedding_ms,
                        "extraction_time_ms": extraction_ms,
                        "extraction_success": success,
                        **metrics,
                    }
                    rows.append(row)

                    print(
                        f"{method}, padding={padding_size}, trial={trial}: "
                        f"extraction={success}, "
                        f"embed={embedding_ms:.2f} ms, "
                        f"extract={extraction_ms:.2f} ms"
                    )

    if not all(row["extraction_success"] for row in rows):
        raise RuntimeError(
            "At least one extraction failed. Review the results before "
            "drawing conclusions."
        )

    with CSV_PATH.open(
        "w", newline="", encoding="utf-8"
    ) as csv_file:
        writer = csv.DictWriter(
            csv_file, fieldnames=list(rows[0].keys())
        )
        writer.writeheader()
        writer.writerows(rows)

    print("\n========== MULTI-COVER EVALUATION COMPLETE ==========")
    print(f"Covers tested: {len(covers)}")
    print(f"Methods: 2")
    print(f"Payload sizes: {len(PADDING_SIZES)}")
    print(f"Trials per configuration: {TRIALS}")
    print(f"Total runs: {len(rows)}")
    print(f"Successful extractions: "
          f"{sum(row['extraction_success'] for row in rows)}/{len(rows)}")
    print(f"CSV saved to: {CSV_PATH}")
    print(
        "\nThese results measure image quality and simple statistics. "
        "They do not by themselves prove resistance to steganalysis."
    )


if __name__ == "__main__":
    main()
