
from PIL import Image
import json


def embed_message(input_image, output_image, message):
    """Hide a text message inside a PNG image using LSB."""

    image = Image.open(input_image).convert("RGB")
    pixels = list(image.get_flattened_data())

    # Convert the message to bytes and add its length as a header.
    message_bytes = message.encode("utf-8")
    header = len(message_bytes).to_bytes(4, byteorder="big")
    payload = header + message_bytes

    # Convert every byte into 8 bits.
    bits = []
    for byte in payload:
        for shift in range(7, -1, -1):
            bits.append((byte >> shift) & 1)

    # Each RGB channel can store one bit in its least significant bit.
    capacity = len(pixels) * 3

    if len(bits) > capacity:
        raise ValueError(
            f"Message too large. Need {len(bits)} bits, "
            f"but image holds only {capacity} bits."
        )

    new_pixels = []
    bit_index = 0

    for pixel in pixels:
        new_pixel = []

        for channel in pixel:
            if bit_index < len(bits):
                channel = (channel & 0b11111110) | bits[bit_index]
                bit_index += 1

            new_pixel.append(channel)

        new_pixels.append(tuple(new_pixel))

    encoded_image = Image.new("RGB", image.size)
    encoded_image.putdata(new_pixels)
    encoded_image.save(output_image, format="PNG")

    print(f"Message embedded successfully: {output_image}")


def extract_message(stego_image):
    """Extract a hidden text message from an image."""

    image = Image.open(stego_image).convert("RGB")

    bits = []
    for pixel in image.get_flattened_data():
        for channel in pixel:
            bits.append(channel & 1)

    # Read the first 32 bits to determine the message length.
    if len(bits) < 32:
        raise ValueError("Image is too small to contain a header.")

    message_length = 0

    for bit in bits[:32]:
        message_length = (message_length << 1) | bit

    required_bits = 32 + message_length * 8

    if required_bits > len(bits):
        raise ValueError("Invalid message length or corrupted image.")

    # Reconstruct the message bytes.
    message_bytes = bytearray()

    for start in range(32, required_bits, 8):
        value = 0

        for bit in bits[start:start + 8]:
            value = (value << 1) | bit

        message_bytes.append(value)

    return message_bytes.decode("utf-8")


if __name__ == "__main__":
    input_path = input("Enter cover PNG path: ").strip()
    output_path = "test_files/stego_image.png"

    metadata = {
        "message": "Hello from the P2P project",
        "peer_id": "peer_001"
    }

    message = json.dumps(metadata)

    try:
        embed_message(input_path, output_path, message)

        extracted = extract_message(output_path)

        print("Extracted metadata:", extracted)
        print("Recovery successful:", extracted == message)

    except (FileNotFoundError, ValueError, OSError, UnicodeDecodeError) as error:
        print("Error:", error)
