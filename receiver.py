
import json
import socket
from pathlib import Path

from integrity import calculate_sha256
from steganography import extract_message

HOST = "127.0.0.1"
PORT = 5001
OUTPUT_DIRECTORY = Path("received_files")


def verify_received_files(file_path, stego_path):
    file_path = Path(file_path)
    stego_path = Path(stego_path)

    # Ensure both received files exist
    if not file_path.is_file():
        print(f"ERROR: Received file not found: {file_path}")
        return

    if not stego_path.is_file():
        print(f"ERROR: Stego image not found: {stego_path}")
        return

    try:
        # Extract hidden metadata from the received image
        hidden_message = extract_message(str(stego_path))
        metadata = json.loads(hidden_message)

        embedded_hash = metadata["sha256"]
        peer_id = metadata.get("peer_id", "unknown")

        # Calculate the hash of the received file
        received_hash = calculate_sha256(str(file_path))

        print("\n========== INTEGRITY VERIFICATION ==========")
        print(f"File: {file_path.name}")
        print(f"Peer ID: {peer_id}")
        print(f"Embedded SHA-256: {embedded_hash}")
        print(f"Received SHA-256: {received_hash}")

        if embedded_hash == received_hash:
            print("\nRESULT: INTEGRITY VERIFIED")
        else:
            print("\nRESULT: INTEGRITY CHECK FAILED - TAMPERING DETECTED")

    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"Integrity verification error: {error}")


def run_verification_receiver():
    OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((HOST, PORT))
        server.listen(1)

        print(f"Integrity receiver listening on {HOST}:{PORT}")
        print("Waiting for sender...")

        connection, address = server.accept()

        with connection:
            print(f"Connected by: {address}")

            from network import receive_file

            receive_file(connection, OUTPUT_DIRECTORY)
            receive_file(connection, OUTPUT_DIRECTORY)

    received_file = OUTPUT_DIRECTORY / "sample.txt"
    received_stego = OUTPUT_DIRECTORY / "stego_image.png"

    verify_received_files(received_file, received_stego)


if __name__ == "__main__":
    run_verification_receiver()
