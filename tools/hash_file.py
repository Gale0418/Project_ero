import hashlib
import sys
from pathlib import Path


CHUNK_SIZE = 16 * 1024 * 1024


def main():
    if len(sys.argv) < 2:
        print("Usage: hash_file.py <file_path>", file=sys.stderr)
        raise SystemExit(1)

    path = Path(sys.argv[1])
    if not path.is_file():
        print(f"Error: {path} is not a file", file=sys.stderr)
        raise SystemExit(1)

    total = path.stat().st_size
    completed = 0
    digest = hashlib.sha256()

    with path.open("rb", buffering=CHUNK_SIZE) as source:
        while chunk := source.read(CHUNK_SIZE):
            digest.update(chunk)
            completed += len(chunk)
            percent = completed * 100 // total
            print(f"SHA256 progress: {percent:3d}% ({completed}/{total} bytes)", file=sys.stderr, flush=True)

    print(digest.hexdigest())


if __name__ == "__main__":
    main()
