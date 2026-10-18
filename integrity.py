
import hashlib


def calculate_sha256(file_path):
    """Calculate the SHA-256 hash of a file."""

    sha256 = hashlib.sha256()

    with open(file_path, "rb") as file:
        while True:
            chunk = file.read(4096)

            if not chunk:
                break

            sha256.update(chunk)

    return sha256.hexdigest()


def verify_integrity(original_hash, received_hash):
    """Return True if both hashes match."""

    return original_hash == received_hash


if __name__ == "__main__":
    file_path = input("Enter the path of the file to check: ").strip()

    try:
        file_hash = calculate_sha256(file_path)

        print("\nFile:", file_path)
        print("SHA-256:", file_hash)
        print("Hash length:", len(file_hash), "characters")

    except FileNotFoundError:
        print("Error: File not found. Check the file path.")

    except PermissionError:
        print("Error: Permission denied.")
