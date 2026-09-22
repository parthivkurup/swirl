"""Ablation holdout a01-a04: image-only extraction.

Each item pairs a promo image (the offer legibly rendered in the graphic) with a
synthetic decorative caption carrying no offer, which forces extraction onto the
image. See tests/fixtures/MANIFEST.md for the set and HOLDOUT.md for what it
measured.

**The images are private and are not committed to this repository.** The `.txt`
and `.expected.json` for each item are here, but the caption alone carries no
offer by construction, so without its image an item cannot be scored: a missing
image would produce an empty extraction indistinguishable from a real miss. Each
item therefore SKIPS when its image is absent rather than running caption-only,
and the whole set skips when no image is present at all.

Place the images at tests/fixtures/holdout/<label>.jpg to run this locally.
"""
import json
from pathlib import Path

import pytest

from compare import compare_fixture
from ingest.extract import load_prompt
from ingest.extractor import CaptionInput, extract_captions
from ingest.fixtures_io import parse_caption
from ingest.hashing import content_hash

HOLDOUT_DIR = Path("tests/fixtures/holdout")
LABELS = [
    "a01_justcraveit_499_imageonly",
    "a02_yomg_3per100g_imageonly",
    "a03_bluspoon_50off_imageonly",
    "a04_yobar_300free_imageonly",
]
SKIP_REASON = (
    "ablation image not present: the a01-a04 promo images are a private set and are "
    "not committed to this repository. The caption alone carries no offer by "
    "construction, so a caption-only run would score a false miss. Place the image "
    "at {path} to run this item."
)


def image_path(label):
    return HOLDOUT_DIR / f"{label}.jpg"


def _require_image(label):
    path = image_path(label)
    if not path.is_file():
        pytest.skip(SKIP_REASON.format(path=path))
    return path


@pytest.fixture(scope="session")
def ablation_extraction(request):
    """Extract every ablation item whose image is present. Skips the whole set when
    none is, so the suite never makes an API call for a set it cannot score."""
    present = [label for label in LABELS if image_path(label).is_file()]
    if not present:
        pytest.skip(SKIP_REASON.format(path=HOLDOUT_DIR / "<label>.jpg"))
    # Only now ask for the extraction client: the private set being absent is the
    # reason this skips on a fresh clone, and it should say so rather than
    # reporting a missing API key.
    gemini_client = request.getfixturevalue("gemini_client")
    inputs = []
    for label in present:
        capture_date, body = parse_caption(HOLDOUT_DIR / f"{label}.txt")
        inputs.append(
            CaptionInput(
                content_hash=content_hash(text=body),
                text=body,
                capture_date=capture_date,
                image_path=str(image_path(label)),
                label=label,
            )
        )
    results, _ = extract_captions(inputs, load_prompt(), gemini_client)
    return {inp.label: actual for inp, actual in zip(inputs, results)}


# a04 is a MEASURED, DOCUMENTED miss, not a regression: the extractor reads a
# numeric price or percentage out of a graphic but can miss a non-priced freebie
# when the caption does not corroborate it (DEFERRED.md records this as a known
# limitation; the same image WITH its real caption extracts, as holdout 035).
# xfail rather than skip, non-strict, so the item is still scored and an XPASS
# announces the day it is fixed instead of passing silently.
KNOWN_MISSES = {"a04_yobar_300free_imageonly": "known limitation: non-priced freebie in an image-only capture"}


@pytest.mark.parametrize(
    "label",
    [
        pytest.param(label, marks=pytest.mark.xfail(reason=KNOWN_MISSES[label], strict=False))
        if label in KNOWN_MISSES
        else label
        for label in LABELS
    ],
)
def test_ablation_item_matches_expected(label, ablation_extraction):
    _require_image(label)
    expected = json.loads((HOLDOUT_DIR / f"{label}.expected.json").read_text(encoding="utf-8"))
    problems = compare_fixture(label, expected, ablation_extraction[label])
    assert not problems, "\n".join(problems)
