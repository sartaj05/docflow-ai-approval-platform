import os
import socket
import time


host = os.environ.get("DATABASE_HOST", "db")
port = int(os.environ.get("DATABASE_PORT", "5432"))
timeout = int(os.environ.get("DATABASE_WAIT_TIMEOUT", "60"))

start_time = time.time()

while True:
    try:
        with socket.create_connection((host, port), timeout=3):
            print(f"PostgreSQL is available at {host}:{port}")
            break

    except OSError:
        elapsed = int(time.time() - start_time)

        if elapsed >= timeout:
            raise RuntimeError(
                f"PostgreSQL was not available after {timeout} seconds."
            )

        print(f"PostgreSQL not ready yet at {host}:{port}. Retrying...")
        time.sleep(2)