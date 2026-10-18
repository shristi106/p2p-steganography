
import struct
from pathlib import Path

import numpy as np
from PIL import Image


def _adaptive_pixel_order(image):
    """
    Rank pixels by local texture using RGB values with their
    two lowest bits cleared. The ranking remains stable after
    LSB embedding.
    """
    rgb = np.asarray(image.convert("RGB"), dtype=np.uint8)

    # Ignore the two lowest bits of every channel when ranking.
    stable_rgb = rgb & np.uint8(0xFC)

    gray = (
        0.299 * stable_rgb[:, :, 0].astype(np.float64)
        + 0.587 * stable_rgb[:, :, 1].astype(np.float64)
        + 0.114 * stable_rgb[:, :, 2].astype(np.float64)
    ).astype(np.uint8)

    padded = np.pad(gray, 1, mode="edge")

    horizontal = np.abs(
        padded[1:-1, 2:].astype(np.int16)
        - padded[1:-1, :-2].astype(np.int16)
    )

    vertical = np.abs(
        padded[2:, 1:-1].astype(np.int16)
        - padded[:-2, 1:-1].astype(np.int16)
    )

    texture_score = horizontal + vertical

    # Deterministic order: highest texture scores first.
    return np.argsort(-texture_score.ravel(), kind="stable")


def _message_bits(message):
    payload = message.encode("utf-8")
    framed = struct.pack("!I", len(payload)) + payload

    return np.unpackbits(
        np.frombuffer(framed, dtype=np.uint8)
    )


def embed_adaptive_message(input_image, output_image, message):
    """Embed a UTF-8 message using texture-adaptive RGB LSBs."""
    with Image.open(input_image) as source:
        image = source.convert("RGB")

    pixels = np.array(image, dtype=np.uint8)
    height, width, _ = pixels.shape

    bits = _message_bits(message)
    order = _adaptive_pixel_order(image)

    capacity_bits = height * width * 3

    if len(bits) > capacity_bits:
        max_payload_bytes = max(0, (capacity_bits // 8) - 4)
        raise ValueError(
            f"Message too large. Approximate maximum payload: "
            f"{max_payload_bytes} bytes."
        )

    flat_pixels = pixels.reshape(-1, 3)

    for bit_index, bit in enumerate(bits):
        pixel_index = order[bit_index // 3]
        channel_index = bit_index % 3

        value = int(flat_pixels[pixel_index, channel_index])
        flat_pixels[pixel_index, channel_index] = (
            (value & 0xFE) | int(bit)
        )

    output_path = Path(output_image)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    Image.fromarray(
        flat_pixels.reshape(height, width, 3)
    ).save(output_path, format="PNG")

    print(f"Adaptive message embedded successfully: {output_path}")


def extract_adaptive_message(stego_image):
    """Extract a message using the same deterministic pixel ranking."""
    with Image.open(stego_image) as source:
        image = source.convert("RGB")

    pixels = np.array(image, dtype=np.uint8)
    flat_pixels = pixels.reshape(-1, 3)
    order = _adaptive_pixel_order(image)

    capacity_bits = flat_pixels.size

    if capacity_bits < 32:
        raise ValueError("Image is too small to contain the message header.")

    def read_bits(start, end):
        result = np.empty(end - start, dtype=np.uint8)

        for index, bit_index in enumerate(range(start, end)):
            pixel_index = order[bit_index // 3]
            channel_index = bit_index % 3

            result[index] = (
                flat_pixels[pixel_index, channel_index] & 1
            )

        return result

    # Read the 4-byte message-length header.
    header_bits = read_bits(0, 32)
    header = np.packbits(header_bits).tobytes()
    payload_length = struct.unpack("!I", header)[0]

    total_bits = 32 + payload_length * 8

    if total_bits > capacity_bits:
        raise ValueError(
            "Invalid message length. The image may be damaged or "
            "may not contain a compatible adaptive message."
        )

    payload_bits = read_bits(32, total_bits)
    payload = np.packbits(payload_bits).tobytes()

    try:
        return payload.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValueError(
            "Message decoding failed. The embedding and extraction "
            "orders do not match, or the image was altered."
        ) from error
