import io

import piexif
import pytest
from PIL import Image

from ingest.images import sanitize_image


def _jpeg_with_gps():
    gps = {
        piexif.GPSIFD.GPSLatitudeRef: "S",
        piexif.GPSIFD.GPSLatitude: [(37, 1), (48, 1), (0, 1)],
        piexif.GPSIFD.GPSLongitudeRef: "E",
        piexif.GPSIFD.GPSLongitude: [(144, 1), (57, 1), (0, 1)],
    }
    exif = piexif.dump({"0th": {piexif.ImageIFD.Make: b"TestCam"}, "GPS": gps, "Exif": {}, "1st": {}, "thumbnail": None})
    buf = io.BytesIO()
    Image.new("RGB", (64, 48), (255, 255, 255)).save(buf, format="JPEG", exif=exif)
    return buf.getvalue()


def test_sanitize_strips_exif_and_gps(tmp_path):
    src = _jpeg_with_gps()
    assert piexif.load(src)["GPS"]  # sanity: input has GPS
    stored, mime = sanitize_image(src, "submissions", root=tmp_path)
    out = piexif.load(str(tmp_path / stored) if not stored.startswith("/") else stored)
    assert not out["GPS"], "GPS not stripped"
    assert not out["0th"], "metadata not stripped"
    assert mime == "image/jpeg"


def test_sanitize_rejects_unsupported(tmp_path):
    with pytest.raises(ValueError):
        sanitize_image(b"not an image", "submissions", root=tmp_path)


def test_stored_path_is_relative_to_media_root(tmp_path, monkeypatch):
    # The whole point of the change: nothing machine-specific reaches the database.
    monkeypatch.setenv("MEDIA_ROOT", str(tmp_path))
    stored, _mime = sanitize_image(_jpeg_with_gps(), "submissions")
    assert not stored.startswith("/"), f"absolute path stored: {stored}"
    assert stored.startswith("submissions/")
    assert (tmp_path / stored).is_file()


def test_resolve_round_trips_a_stored_path(tmp_path, monkeypatch):
    from ingest.media import resolve

    monkeypatch.setenv("MEDIA_ROOT", str(tmp_path))
    stored, _mime = sanitize_image(_jpeg_with_gps(), "submissions")
    assert resolve(stored).is_file()


def test_resolve_passes_through_legacy_absolute_paths(tmp_path, monkeypatch):
    from ingest.media import resolve

    monkeypatch.setenv("MEDIA_ROOT", str(tmp_path / "elsewhere"))
    legacy = tmp_path / "old.jpg"
    legacy.write_bytes(b"x")
    assert resolve(str(legacy)) == legacy
