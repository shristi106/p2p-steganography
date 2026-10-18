
# P2P Steganography and File Integrity

A Python project exploring image-based LSB steganography, SHA-256 file integrity verification, and TCP file transfer.

## Features

- SHA-256 hashing and integrity verification
- Fixed-order RGB LSB message embedding and extraction
- Experimental adaptive LSB embedding and extraction
- TCP sender and receiver for file transfer
- Tampering detection tests
- Image quality and performance evaluation
- Preliminary statistical steganalysis experiments

## Technologies

- Python
- Pillow
- NumPy
- scikit-image
- pandas
- scikit-learn
- TCP sockets

## Setup

Create and activate a virtual environment.

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install the dependencies:

```powershell
python -m pip install pillow numpy scikit-image pandas scikit-learn
```

## Running the project

Run individual scripts from the project root:

```powershell
python prepare_transfer.py
python test_tampering.py
python evaluation.py
python compare_steganography.py
python evaluate_steganalysis.py
python evaluate_multiple_covers.py
python summarize_evaluation.py
python steganalysis_detector.py
```

Follow each script's prompts and instructions. The sender and receiver should be run in separate terminals when testing TCP transfer.

## Experimental limitations

Adaptive LSB is experimental and has not been established as resistant to steganalysis. The current detector evaluation includes synthetic cover-like images and a small number of other images. Further evaluation using diverse real photographs is required.

Embedding a SHA-256 hash provides an integrity comparison, but by itself does not authenticate the sender. This project is for educational and research purposes.

## License

No license has been selected yet.
