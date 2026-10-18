
import json
from integrity import calculate_sha256
from steganography import embed_message, extract_message


def prepare_transfer(file_path, cover_path, output_image):
    # Calculate the hash of the original file.
    file_hash = calculate_sha256(file_path)

    # Prepare metadata to hide inside the cover image.
    metadata = {
        "file_name": file_path.split("/")[-1].split("\\")[-1],
        "sha256": file_hash,
        "peer_id": "peer_001"
    }

    message = json.dumps(metadata)

    # Embed metadata in the PNG image.
    embed_message(cover_path, output_image, message)

    # Extract the metadata to verify it was embedded correctly.
    recovered_message = extract_message(output_image)
    recovered_metadata = json.loads(recovered_message)

    print("\n--- Transfer Preparation Results ---")
    print("Original file:", metadata["file_name"])
    print("Original SHA-256:", file_hash)
    print("Extracted SHA-256:", recovered_metadata["sha256"])
    print("Metadata recovered:", recovered_metadata == metadata)

    return recovered_metadata


if __name__ == "__main__":
    file_path = input("Enter file to send: ").strip()
    cover_path = input("Enter cover PNG path: ").strip()

    output_image = "test_files/stego_image.png"

    try:
        prepare_transfer(file_path, cover_path, output_image)

    except (FileNotFoundError, ValueError, OSError, UnicodeDecodeError) as error:
        print("Error:", error)
