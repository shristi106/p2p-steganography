
from pathlib import Path
from PIL import Image

SOURCE_DIR = Path(r"C:\path\to\extracted\BOSSbase")
OUTPUT_DIR = Path("test_files/covers_png")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

extensions = {".pgm", ".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}

files = sorted(
    path for path in SOURCE_DIR.rglob("*")
    if path.is_file() and path.suffix.lower() in extensions
)

if len(files) < 30:
    raise RuntimeError(
        f"Found only {len(files)} images. Check SOURCE_DIR."
    )

converted = 0

for index, source in enumerate(files[:30], start=1):
    destination = OUTPUT_DIR / f"boss_cover_{index:03d}.png"

    try:
        with Image.open(source) as image:
            # Convert grayscale images to RGB for consistent processing.
            image.convert("RGB").save(destination, format="PNG")

        converted += 1
        print(f"Saved {destination}")

    except Exception as error:
        print(f"Skipped {source.name}: {error}")

print(f"\nDataset preparation complete: {converted} images converted.")
print(f"Output folder: {OUTPUT_DIR.resolve()}")
