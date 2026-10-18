
from pathlib import Path
from PIL import Image

input_folder = Path("test_files/covers")
output_folder = Path("test_files/covers_png")
output_folder.mkdir(parents=True, exist_ok=True)

supported_extensions = {".jpg", ".jpeg", ".avif", ".png", ".webp"}

for image_path in input_folder.iterdir():
    if image_path.suffix.lower() not in supported_extensions:
        continue

    try:
        with Image.open(image_path) as image:
            # Convert to RGB and save as lossless PNG.
            image = image.convert("RGB")
            output_path = output_folder / f"{image_path.stem}.png"
            image.save(output_path, format="PNG")
            print(f"Converted: {image_path.name} -> {output_path}")

    except Exception as error:
        print(f"Could not convert {image_path.name}: {error}")

print("\nConversion complete.")
