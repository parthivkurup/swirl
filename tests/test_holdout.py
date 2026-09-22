"""Natural holdout 031-041: real out-of-sample captures.

Eleven captures drawn from real monitored accounts and hand-labelled before the
extractor was run against them. This is the generalisation reference: unlike the
30 in `captions/`, the prompt has never been shaped against these. See
tests/fixtures/HOLDOUT.md for the policy and the recorded results.

**The captions are a private set and are not committed to this repository.** They
reproduce real posts verbatim, so the `.txt`/`.expected.json` pairs are held
outside the public tree. Each item SKIPS when its caption is absent rather than
being silently dropped from the run, so the set stays visible as a thing that
exists and is not being measured here.

Place the pairs at tests/fixtures/holdout/<label>.txt and <label>.expected.json
to run this locally.
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
    "031_yomg_per_100g",
    "032_froyolicious_bottleflip_15",
    "033_yoart_loyalty_signup",
    "034_yomg_3_per_100g",
    "035_yobar_canberra_300_free",
    "036_yochi_steps_bogo_freebie",
    "037_yoto_closed_tomorrow",
    "038_goje_pistachio_back",
    "039_yoway_reel_no_offer",
    "040_yoart_glen_opening_feature",
    "041_froyolicious_influencer_no_offer",
]
SKIP_REASON = (
    "holdout caption not present: the 031-041 natural holdout captions are a private "
    "set and are not committed to this repository, because they reproduce real posts "
    "verbatim. Place the pair at {path} and its .expected.json to run this item."
)


def caption_path(label):
    return HOLDOUT_DIR / f"{label}.txt"


def expected_path(label):
    return HOLDOUT_DIR / f"{label}.expected.json"


def _present(label):
    return caption_path(label).is_file() and expected_path(label).is_file()


def _require_caption(label):
    if not _present(label):
        pytest.skip(SKIP_REASON.format(path=caption_path(label)))


@pytest.fixture(scope="session")
def holdout_extraction(request):
    """Extract every holdout item whose caption is present. Skips the whole set when
    none is, so the suite never makes an API call for a set it cannot score."""
    present = [label for label in LABELS if _present(label)]
    if not present:
        pytest.skip(SKIP_REASON.format(path=HOLDOUT_DIR / "<label>.txt"))
    # Only now ask for the extraction client: the private set being absent is the
    # reason this skips on a fresh clone, and it should say so rather than
    # reporting a missing API key.
    gemini_client = request.getfixturevalue("gemini_client")
    inputs = []
    for label in present:
        capture_date, body = parse_caption(caption_path(label))
        inputs.append(
            CaptionInput(
                content_hash=content_hash(text=body),
                text=body,
                capture_date=capture_date,
                label=label,
            )
        )
    results, _ = extract_captions(inputs, load_prompt(), gemini_client)
    return {inp.label: actual for inp, actual in zip(inputs, results)}


# 032's store_hint divergence is an unresolved POLICY question, not a model error:
# should a suburb a business names in its own prose ("try docklands best froyo")
# populate store_hint? The hand label says null, the extractor says "Docklands",
# and HOLDOUT.md records both readings rather than settling them. xfail non-strict
# so the item is still scored and an XPASS shows up the day the policy is decided.
KNOWN_DIVERGENCES = {
    "032_froyolicious_bottleflip_15": "unresolved policy question: suburb named in a business's own prose",
}


@pytest.mark.parametrize(
    "label",
    [
        pytest.param(label, marks=pytest.mark.xfail(reason=KNOWN_DIVERGENCES[label], strict=False))
        if label in KNOWN_DIVERGENCES
        else label
        for label in LABELS
    ],
)
def test_holdout_item_matches_expected(label, holdout_extraction):
    _require_caption(label)
    expected = json.loads(expected_path(label).read_text(encoding="utf-8"))
    problems = compare_fixture(label, expected, holdout_extraction[label])
    assert not problems, "\n".join(problems)
