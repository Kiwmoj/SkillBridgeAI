import socket
from threading import Thread
from time import monotonic, sleep

import uvicorn
from alembic import command
from alembic.config import Config

from desktop.main import main as open_desktop


def main() -> int:
    command.upgrade(Config("alembic.ini"), "head")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        port = listener.getsockname()[1]
        server = uvicorn.Server(uvicorn.Config("backend.main:app", access_log=False, timeout_graceful_shutdown=5))
        worker = Thread(target=server.run, kwargs={"sockets": [listener]})
        worker.start()
        try:
            deadline = monotonic() + 20
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
