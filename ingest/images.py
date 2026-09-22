import hashlib
from io import BytesIO
from pathlib import Path

import pillow_heif
from PIL import Image, ImageOps

from ingest.media import media_root, to_stored

pillow_heif.register_heif_opener()

# Accepted decoded formats. HEIC/HEIF decode to Pillow format "HEIF".
_ALLOWED = {"JPEG", "PNG", "HEIF"}


def sanitize_image(src_bytes, subdir, root=None):
    """Decode an uploaded image, bake in EXIF orientation, then re-encode WITHOUT
    any metadata. Re-encoding drops all EXIF including GPS, so a photo of a shop
    sign cannot carry the submitter's location. HEIC is converted to JPEG (also
    fixes browser display). Raises ValueError on an unsupported format.

    Writes to <root>/<subdir>/<sha256><ext>, where root defaults to the media
    root. Returns (stored_path, mime), and stored_path is relative to the media
    root so nothing machine-specific reaches the database."""
    try:
        im = Image.open(BytesIO(src_bytes))
        im.load()
    except Exception as e:
        raise ValueError(f"unreadable image: {e}") from e
    fmt = (im.format or "").upper()
    if fmt not in _ALLOWED:
        raise ValueError(f"unsupported image format: {fmt or 'unknown'}")

    im = ImageOps.exif_transpose(im)  # apply orientation, then metadata is dropped on save

    if fmt == "PNG":
        out_fmt, ext, mime = "PNG", ".png", "image/png"
        im = im.convert("RGBA") if im.mode in ("RGBA", "LA", "P") else im.convert("RGB")
    else:  # JPEG or HEIF -> JPEG
        out_fmt, ext, mime = "JPEG", ".jpg", "image/jpeg"
        im = im.convert("RGB")

    buf = BytesIO()
    im.save(buf, format=out_fmt)  # no exif= argument: all metadata dropped
    data = buf.getvalue()

    h = hashlib.sha256(data).hexdigest()
    out = Path(root) if root is not None else media_root()
    out = (out / subdir).resolve()
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{h}{ext}"
    path.write_bytes(data)
    return to_stored(path), mime
