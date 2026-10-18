
from integrity import calculate_sha256
from steganography import extract_message
import json

original_hash = json.loads(
    extract_message("received_files/stego_image.png")
)["sha256"]

received_hash = calculate_sha256("received_files/sample.txt")

print("Embedded SHA-256:", original_hash)
print("Modified file SHA-256:", received_hash)

if original_hash == received_hash:
    print("RESULT: INTEGRITY VERIFIED")
else:
    print("RESULT: INTEGRITY CHECK FAILED - TAMPERING DETECTED")
