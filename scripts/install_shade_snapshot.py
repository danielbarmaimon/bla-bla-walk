"""Install the committed shade inputs into the existing local loader paths."""

import argparse
import hashlib
import json
import shutil
import tempfile
from pathlib import Path, PurePosixPath
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = "data/prepared/shade-basel-v1.json"


def digest(path):
    """Hash a prepared artifact without loading a raster into memory."""
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def input_digest(path):
    """Compare JSON content across Windows and Unix checkout line endings."""
    content = json.loads(path.read_text(encoding="utf-8"))
    canonical = json.dumps(content, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def install(root=ROOT, *, replace=False):
    """Verify all inputs before writing; preserve differing local data by default."""
    root = Path(root).resolve()
    metadata = json.loads((root / SNAPSHOT).read_text(encoding="utf-8"))
    archive_name = metadata["archive"]
    if Path(archive_name).name != archive_name or not archive_name.endswith(".zip"):
        raise ValueError("Invalid snapshot archive name")
    archive = root / "data/prepared" / archive_name
    if digest(archive) != metadata["sha256"]:
        raise ValueError("Snapshot archive checksum mismatch")
    for name, checksum in metadata["inputs"].items():
        if name not in {
            "config/geometry.json",
            "config/building-shade.json",
            "data/tile-inventory.json",
            "data/routes/demo.geojson",
        }:
            raise ValueError("Invalid snapshot input path")
        if input_digest(root / name) != checksum:
            raise ValueError(f"Snapshot does not match current input: {name}")
    files = metadata["files"]
    # A complete local dataset can legitimately differ from the committed
    # snapshot. Keep that directory as a unit (including its manifest) and
    # restore only a dataset whose manifest is missing. Copying snapshot tiles
    # beside local tiles while publishing the snapshot manifest would make the
    # resulting dataset internally inconsistent.
    existing_datasets = {
        directory
        for directory in ("data/geometry", ".cache/buildings")
        if (root / directory / "manifest.json").is_file()
    }
    for name in files:
        path = PurePosixPath(name)
        if (
            str(path) != name
            or ".." in path.parts
            or "\\" in name
            or len(path.parts) != 3
            or str(path.parent) not in {"data/geometry", ".cache/buildings"}
            or path.suffix not in {".json", ".tif", ".npy"}
        ):
            raise ValueError(f"Invalid snapshot destination: {name}")
        if str(path.parent) in existing_datasets:
            continue
        destination = root / name
        if not destination.resolve().is_relative_to(root):
            raise ValueError(f"Snapshot destination escapes checkout: {name}")
        if (
            destination.exists()
            and digest(destination) != files[name]["sha256"]
            and not replace
        ):
            raise ValueError(
                f"Different local data exists: {name}; use --replace to restore snapshot"
            )
    with tempfile.TemporaryDirectory(prefix="shade-snapshot-", dir=root) as temporary:
        staging = Path(temporary)
        with ZipFile(archive) as bundle:
            if sorted(bundle.namelist()) != sorted(files):
                raise ValueError("Snapshot archive file list mismatch")
            for name, record in files.items():
                if PurePosixPath(name).parent.as_posix() in existing_datasets:
                    continue
                info = bundle.getinfo(name)
                if info.file_size != record["bytes"]:
                    raise ValueError(f"Snapshot size mismatch: {name}")
                target = staging / name
                target.parent.mkdir(parents=True, exist_ok=True)
                with bundle.open(name) as source, target.open("wb") as output:
                    shutil.copyfileobj(source, output)
                if digest(target) != record["sha256"]:
                    raise ValueError(f"Snapshot file checksum mismatch: {name}")
        # Publish manifests last so incomplete copies cannot appear complete.
        selected_files = {
            name: record
            for name, record in files.items()
            if PurePosixPath(name).parent.as_posix() not in existing_datasets
        }
        for name in sorted(
            selected_files, key=lambda value: value.endswith("/manifest.json")
        ):
            destination = root / name
            if (
                destination.exists()
                and digest(destination) == selected_files[name]["sha256"]
            ):
                continue
            destination.parent.mkdir(parents=True, exist_ok=True)
            partial = destination.with_name(destination.name + ".snapshot-part")
            shutil.copyfile(staging / name, partial)
            partial.replace(destination)
    return len(selected_files)


def main():
    """Restore a pinned local dataset without contacting any provider."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--replace", action="store_true", help="Replace differing local prepared inputs"
    )
    args = parser.parse_args()
    try:
        count = install(replace=args.replace)
    except (OSError, ValueError, KeyError) as error:
        parser.exit(1, f"Snapshot installation failed: {error}\n")
    print(f"Verified and installed {count} shade inputs; no network requests")


if __name__ == "__main__":
    main()
