"""Where capture images live, and how their paths are stored.

image_path in the database is stored RELATIVE to the media root ("submissions/
<hash>.jpg"), never absolute. An absolute path bakes one machine's directory
layout into the data: it breaks the moment the repo moves, the checkout is
cloned, or the reader runs anywhere other than the machine that wrote it.

The root itself is configuration (MEDIA_ROOT), defaulting to <repo>/media.
"""
import os
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent


def media_root() -> Path:
    env = (os.environ.get("MEDIA_ROOT") or "").strip()
    root = Path(env).expanduser() if env else _REPO_ROOT / "media"
    return root.resolve()


def to_stored(path) -> str:
    """An absolute path on disk, as it should be recorded in the database."""
    p = Path(path).resolve()
    try:
        return p.relative_to(media_root()).as_posix()
    except ValueError:
        # Outside the media root (a test tmpdir, or a one-off manual capture).
        # Storing it absolute is still wrong-ish, but inventing a relative path
        # that resolves somewhere else would be worse.
        return str(p)


def resolve(stored: str) -> Path:
    """A stored image_path, resolved to a real file.

    Absolute values are legacy rows written before paths became relative, plus
    manual captures pointing outside the media root; they are returned as-is.
    A relative value is normally under the media root, but the manual CLI also
    accepts a path relative to the working directory, so that is the fallback.
    """
    p = Path(stored)
    if p.is_absolute():
        return p
    under_root = media_root() / p
    return under_root if under_root.exists() else p
