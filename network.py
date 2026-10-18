
import socket
import struct
import time
from pathlib import Path

HOST = "127.0.0.1"
PORT = 5001


def send_file(connection, file_path):
    file_path = Path(file_path)

    if not file_path.is_file():
        raise FileNotFoundError(f"File not found: {file_path}")

    filename = file_path.name.encode("utf-8")
    file_size = file_path.stat().st_size

    # Send filename length, filename, and file size
    connection.sendall(struct.pack("!I", len(filename)))
    connection.sendall(filename)
    connection.sendall(struct.pack("!Q", file_size))

    # Send file contents
    with file_path.open("rb") as file:
        while True:
            chunk = file.read(4096)

            if not chunk:
                break

            connection.sendall(chunk)

    print(f"Sent: {file_path.name} ({file_size} bytes)")


def receive_exact(connection, num_bytes):
    data = bytearray()

    while len(data) < num_bytes:
        chunk = connection.recv(num_bytes - len(data))

        if not chunk:
            raise ConnectionError("Connection closed before all data arrived.")

        data.extend(chunk)

    return bytes(data)


def receive_file(connection, output_directory):
    output_directory = Path(output_directory)
    output_directory.mkdir(parents=True, exist_ok=True)

    # Receive filename
    filename_length = struct.unpack(
        "!I", receive_exact(connection, 4)
    )[0]

    filename = receive_exact(
        connection, filename_length
    ).decode("utf-8")

    # Prevent directory traversal
    filename = Path(filename).name

    # Receive file size
    file_size = struct.unpack(
        "!Q", receive_exact(connection, 8)
    )[0]

    output_path = output_directory / filename
    bytes_received = 0

    with output_path.open("wb") as file:
        while bytes_received < file_size:
            chunk_size = min(4096, file_size - bytes_received)
            chunk = receive_exact(connection, chunk_size)

            file.write(chunk)
            bytes_received += len(chunk)

    print(f"Received: {filename} ({bytes_received} bytes)")


def run_receiver():
    output_directory = "received_files"

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((HOST, PORT))
        server.listen(1)

        print(f"Receiver listening on {HOST}:{PORT}")
        print("Waiting for sender...")

        connection, address = server.accept()

        with connection:
            print(f"Connected by: {address}")

            # Receive exactly two files, as in the existing project
            receive_file(connection, output_directory)
            receive_file(connection, output_directory)

    print("Transfer received successfully.")


def run_sender():
    files_to_send = [
        "test_files/sample.txt",
        "test_files/stego_image.png",
    ]

    # Check that both files exist before connecting
    for file_path in files_to_send:
        if not Path(file_path).is_file():
            print(f"File not found: {file_path}")
            return

    total_bytes = sum(
        Path(file_path).stat().st_size
        for file_path in files_to_send
    )

    start_time = time.perf_counter()

    try:
        with socket.create_connection(
            (HOST, PORT), timeout=10
        ) as connection:
            print("Connected to receiver.")

            for file_path in files_to_send:
                send_file(connection, file_path)

        elapsed_time = time.perf_counter() - start_time

        throughput_kbps = (
            total_bytes / elapsed_time / 1024
            if elapsed_time > 0
            else 0
        )

        print("\n========== NETWORK PERFORMANCE ==========")
        print(f"Total data transferred: {total_bytes} bytes")
        print(f"Transfer time: {elapsed_time:.6f} seconds")
        print(f"Throughput: {throughput_kbps:.2f} KB/s")
        print("Transfer complete.")

    except (OSError, TimeoutError, ConnectionError) as error:
        print(f"Transfer failed: {error}")


if __name__ == "__main__":
    choice = input("Run as sender or receiver? (s/r): ").strip().lower()

    if choice == "s":
        run_sender()
    elif choice == "r":
        run_receiver()
    else:
        print("Invalid choice. Enter 's' for sender or 'r' for receiver.")
