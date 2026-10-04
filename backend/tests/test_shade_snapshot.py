"""Exercise safe offline restore with corruption and existing local data."""

import hashlib
import json
import sys
from pathlib import Path
from zipfile import ZipFile

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from install_shade_snapshot import SNAPSHOT, input_digest, install  # noqa: E402


@pytest.fixture
def snapshot(tmp_path):
    directory = tmp_path / "data/prepared"
    directory.mkdir(parents=True)
    name = ".cache/buildings/manifest.json"
    payload = b'{"example": true}\n'
    archive = directory / "shade-basel-v1.zip"
    with ZipFile(archive, "w") as bundle:
        bundle.writestr(name, payload)
    metadata = {
        "archive": archive.name,
        "sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "inputs": {},
        "files": {
            name: {"sha256": hashlib.sha256(payload).hexdigest(), "bytes": len(payload)}
        },
    }
    (tmp_path / SNAPSHOT).write_text(json.dumps(metadata))
    return tmp_path, metadata, payload


def test_restore_reuses_identical_files_and_preserves_different_local_data(snapshot):
    root, _, payload = snapshot
    assert install(root) == 1
    destination = root / ".cache/buildings/manifest.json"
    assert destination.read_bytes() == payload
    stamp = destination.stat().st_mtime_ns
    assert install(root) == 1
    assert destination.stat().st_mtime_ns == stamp
    destination.write_bytes(b"newer local data")
    with pytest.raises(ValueError, match="Different local data"):
        install(root)
    assert destination.read_bytes() == b"newer local data"
    install(root, replace=True)
    assert destination.read_bytes() == payload


def test_corrupt_archive_never_publishes_files(snapshot):
    root, _, _ = snapshot
    with (root / "data/prepared/shade-basel-v1.zip").open("ab") as stream:
        stream.write(b"corruption")
    with pytest.raises(ValueError, match="archive checksum"):
        install(root)
    assert not (root / ".cache").exists()


def test_corrupt_member_never_publishes_files(snapshot):
    root, metadata, _ = snapshot
    metadata["files"][".cache/buildings/manifest.json"]["sha256"] = "0" * 64
    (root / SNAPSHOT).write_text(json.dumps(metadata))
    with pytest.raises(ValueError, match="file checksum"):
        install(root)
    assert not (root / ".cache").exists()


@pytest.mark.parametrize("name", ["../outside.json", ".cache/buildings/../escape.json"])
def test_rejects_paths_outside_dataset(snapshot, name):
    root, metadata, _ = snapshot
    metadata["files"] = {name: {"sha256": "0" * 64, "bytes": 1}}
    (root / SNAPSHOT).write_text(json.dumps(metadata))
    with pytest.raises(ValueError, match="Invalid snapshot destination"):
        install(root)


def test_configuration_mismatch_never_publishes_files(snapshot):
    root, metadata, _ = snapshot
    (root / "config").mkdir()
    (root / "config/geometry.json").write_text("{}")
    metadata["inputs"] = {"config/geometry.json": "0" * 64}
    (root / SNAPSHOT).write_text(json.dumps(metadata))
    with pytest.raises(ValueError, match="does not match current input"):
        install(root)
    assert not (root / ".cache").exists()


def test_input_hash_ignores_checkout_line_endings(tmp_path):
    path = tmp_path / "config.json"
    path.write_bytes(b'{\n  "setting": 1\n}\n')
    original = input_digest(path)
    path.write_bytes(b'{\r\n  "setting": 1\r\n}\r\n')
    assert input_digest(path) == original
    path.write_text('{"setting": 2}')
    assert input_digest(path) != original
