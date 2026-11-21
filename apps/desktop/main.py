"""Entry point for the SkillBridge AI desktop app: ``python -m apps.desktop.main``."""
import sys

from apps.desktop.application import run


def main(backend_url: str | None = None) -> int:
    return run(backend_url)


if __name__ == "__main__":
    sys.exit(main())
