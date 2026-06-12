from __future__ import annotations

import argparse
import gzip
import shutil
from pathlib import Path


def gzip_file(src: Path, overwrite: bool = False) -> Path:
    if not src.exists():
        raise FileNotFoundError(f"Input file not found: {src}")

    if not src.is_file():
        raise ValueError(f"Input path not a file: {src}")

    dst = src.with_suffix(src.suffix + ".gz")

    if dst.exists() and not overwrite:
        raise FileExistsError(f"Output already exists: {dst}. Use --overwrite to replace it")

    with src.open("rb") as f_in, gzip.open(dst, "wb", compresslevel=9) as f_out:
        shutil.copyfileobj(f_in, f_out, length=1024 * 1024 * 16)

    return dst


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compress single named file to .gz for large CSV outputs"
    )
    parser.add_argument("path", help="Path to file to compress")
    parser.add_argument("--overwrite", action="store_true", help="Replace existing .gz output")

    args = parser.parse_args()

    src = Path(args.path)
    dst = gzip_file(src, overwrite=args.overwrite)

    print(f"Created: {dst}")
    print(f"Original size MB: {src.stat().st_size / 1024 / 1024:,.1f}")
    print(f"Gzip size MB:    {dst.stat().st_size / 1024 / 1024:,.1f}")


if __name__ == "__main__":
    main()