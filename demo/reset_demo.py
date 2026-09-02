"""Reset demo database."""

from __future__ import annotations

from pathlib import Path

from ledgermind.config import get_settings


def main() -> None:
    settings = get_settings()
    db_path = Path(settings.sibyl_memory_db)
    if db_path.exists():
        db_path.unlink()
    for suffix in ("-wal", "-shm"):
        wal = Path(str(db_path) + suffix)
        if wal.exists():
            wal.unlink()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"reset: {db_path}")


if __name__ == "__main__":
    main()
