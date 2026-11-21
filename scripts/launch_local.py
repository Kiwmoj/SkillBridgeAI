"""Run the API and the desktop together on a free loopback port for local use.

Migrates the configured database, starts uvicorn in a thread, opens the desktop against it, and
stops the server when the desktop closes.
"""
import socket
import sys
from pathlib import Path
from threading import Thread
from time import monotonic, sleep

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import uvicorn  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402

from apps.desktop.main import main as open_desktop  # noqa: E402

STARTUP_TIMEOUT_SECONDS = 20


def main() -> int:
    command.upgrade(Config(str(ROOT / "alembic.ini")), "head")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        port = listener.getsockname()[1]
        server = uvicorn.Server(uvicorn.Config("apps.backend.main:app", access_log=False, timeout_graceful_shutdown=5))
        worker = Thread(target=server.run, kwargs={"sockets": [listener]})
        worker.start()
        try:
            deadline = monotonic() + STARTUP_TIMEOUT_SECONDS
            while not server.started:
                if not worker.is_alive() or monotonic() >= deadline:
                    raise RuntimeError("Local backend did not start; check the startup log above.")
                sleep(0.05)
            return open_desktop(f"http://127.0.0.1:{port}")
        finally:
            server.should_exit = True
            worker.join()


if __name__ == "__main__":
    raise SystemExit(main())
