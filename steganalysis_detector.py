
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import LeaveOneGroupOut
from sklearn.metrics import (
    accuracy_score,
    roc_auc_score,
    precision_score,
    recall_score,
)

from steganography import embed_message
from adaptive_steganography import embed_adaptive_message


# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
COVERS_DIR = BASE_DIR / "test_files" / "covers_png"
OUTPUT_DIR = BASE_DIR / "test_files" / "detector_dataset"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

PAYLOAD_SIZES = [128, 512]
RANDOM_STATE = 42


# --------------------------------------------------
# FEATURE EXTRACTION
# --------------------------------------------------

def extract_features(image_path):
    image = np.asarray(
        Image.open(image_path).convert("RGB"),
        dtype=np.float32
    )

    features = []

    # Pixel intensity statistics for each RGB channel.
    for channel in range(3):
        plane = image[:, :, channel]

        features.extend([
            float(np.mean(plane)),
            float(np.std(plane)),
            float(np.mean(np.abs(np.diff(plane, axis=0)))),
            float(np.mean(np.abs(np.diff(plane, axis=1)))),
        ])

    # Least-significant-bit statistics.
    lsb = image.astype(np.uint8) & 1

    features.append(float(np.mean(lsb)))

    for channel in range(3):
        plane = lsb[:, :, channel]

        features.append(float(np.mean(plane)))

        if plane.shape[1] > 1:
            features.append(
                float(np.mean(plane[:, 1:] == plane[:, :-1]))
            )
            features.append(
                float(np.mean(plane[:, 1:] != plane[:, :-1]))
            )

        if plane.shape[0] > 1:
            features.append(
                float(np.mean(plane[1:, :] == plane[:-1, :]))
            )
            features.append(
                float(np.mean(plane[1:, :] != plane[:-1, :]))
            )

    # Adjacent-pixel absolute differences for RGB channels.
    for channel in range(3):
        plane = image[:, :, channel]

        horizontal = np.abs(
            plane[:, 1:] - plane[:, :-1]
        )
        vertical = np.abs(
            plane[1:, :] - plane[:-1, :]
        )

        features.extend([
            float(np.mean(horizontal)),
            float(np.std(horizontal)),
            float(np.mean(vertical)),
            float(np.std(vertical)),
        ])

    return features


# --------------------------------------------------
# CREATE COVER/STego SAMPLES
# --------------------------------------------------

def build_dataset(method, cover_paths):
    rows = []

    for cover_path in cover_paths:
        cover_name = cover_path.name

        print(f"\nProcessing cover: {cover_name}")

        # Original cover image: label 0.
        rows.append({
            "cover": cover_name,
            "method": method,
            "label": 0,
            "payload_bytes": 0,
            "features": extract_features(cover_path),
        })

        for payload_size in PAYLOAD_SIZES:
            # ASCII character A occupies one byte.
            message = "A" * payload_size

            output_path = OUTPUT_DIR / (
                f"{cover_path.stem}_{method}_{payload_size}.png"
            )

            if method == "fixed":
                embed_message(
                    str(cover_path),
                    str(output_path),
                    message,
                )
            else:
                embed_adaptive_message(
                    str(cover_path),
                    str(output_path),
                    message,
                )

            rows.append({
                "cover": cover_name,
                "method": method,
                "label": 1,
                "payload_bytes": payload_size,
                "features": extract_features(output_path),
            })

            print(f"Generated: {output_path.name}")

    return rows


# --------------------------------------------------
# GROUPED CROSS-VALIDATION
# --------------------------------------------------

def evaluate_method(method, cover_paths):
    print(f"\n{'=' * 60}")
    print(f"EVALUATING {method.upper()} LSB")
    print("=" * 60)

    rows = build_dataset(method, cover_paths)

    X = np.asarray([row["features"] for row in rows])
    y = np.asarray([row["label"] for row in rows])
    groups = np.asarray([row["cover"] for row in rows])

    logo = LeaveOneGroupOut()

    # Collect predictions across held-out cover groups.
    all_labels = []
    all_predictions = []
    all_probabilities = []

    for train_index, test_index in logo.split(X, y, groups):
        model = RandomForestClassifier(
            n_estimators=200,
            random_state=RANDOM_STATE,
            class_weight="balanced",
        )

        model.fit(X[train_index], y[train_index])

        predictions = model.predict(X[test_index])
        probabilities = model.predict_proba(X[test_index])[:, 1]

        all_labels.extend(y[test_index])
        all_predictions.extend(predictions)
        all_probabilities.extend(probabilities)

    accuracy = accuracy_score(all_labels, all_predictions)
    precision = precision_score(
        all_labels, all_predictions, zero_division=0
    )
    recall = recall_score(
        all_labels, all_predictions, zero_division=0
    )
    auc = roc_auc_score(all_labels, all_probabilities)

    print(f"Samples: {len(rows)}")
    print(f"Distinct cover images: {len(cover_paths)}")
    print(f"Accuracy:  {accuracy:.4f}")
    print(f"Precision: {precision:.4f}")
    print(f"Recall:    {recall:.4f}")
    print(f"ROC-AUC:   {auc:.4f}")

    return {
        "method": method,
        "cover_images": len(cover_paths),
        "samples": len(rows),
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "roc_auc": auc,
    }


# --------------------------------------------------
# MAIN
# --------------------------------------------------

if __name__ == "__main__":
    cover_paths = sorted(
        path for path in COVERS_DIR.glob("*.png")
        if path.is_file()
    )

    if len(cover_paths) < 5:
        raise RuntimeError(
            f"Found only {len(cover_paths)} PNG images in "
            f"{COVERS_DIR}. Add at least 5 cover images."
        )

    print(f"Found {len(cover_paths)} cover images.")

    results = []

    for method in ["fixed", "adaptive"]:
        results.append(evaluate_method(method, cover_paths))

    results_df = pd.DataFrame(results)

    csv_path = BASE_DIR / "steganalysis_detector_results.csv"
    results_df.to_csv(csv_path, index=False)

    print("\nFINAL COMPARISON")
    print(results_df.to_string(index=False))
    print(f"\nResults saved to: {csv_path}")

    print(
        "\nInterpretation: ROC-AUC near 0.5 indicates chance-level "
        "ranking on this evaluation. A higher score indicates "
        "better separation. These results alone do not prove "
        "steganographic security."
    )
