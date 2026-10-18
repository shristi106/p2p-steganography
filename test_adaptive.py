
import json
from pathlib import Path

from integrity import calculate_sha256
from adaptive_steganography import (
    embed_adaptive_message,
    extract_adaptive_message,
)

original_file = Path("test_files/sample.txt")
cover_image = Path("test_files/cover.png")
output_image = Path("test_files/adaptive_stego.png")

if not original_file.is_file():
    raise FileNotFoundError(f"Missing file: {original_file}")

if not cover_image.is_file():
    raise FileNotFoundError(f"Missing image: {cover_image}")

metadata = {
    "file_name": original_file.name,
    "sha256": calculate_sha256(str(original_file)),
    "peer_id": "peer_001",
}

message = json.dumps(metadata)

embed_adaptive_message(
    cover_image,
    output_image,
    message,
)

extracted_message = extract_adaptive_message(output_image)
extracted_metadata = json.loads(extracted_message)

print("\n========== ADAPTIVE LSB TEST ==========")
print("Metadata extraction successful:", extracted_metadata == metadata)
print("Original SHA-256:", metadata["sha256"])
print("Extracted SHA-256:", extracted_metadata["sha256"])
print("Hash matches:", extracted_metadata["sha256"] == metadata["sha256"])
print("Output image:", output_image)
