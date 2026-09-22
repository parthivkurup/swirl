import mimetypes
import os
import time
from pathlib import Path

from google import genai
from google.genai import types

from ingest.log import log
from ingest.media import resolve as resolve_media
from ingest.schemas import BatchResult

PRIMARY_MODEL = "gemini-flash-latest"
FALLBACK_MODEL = "gemini-flash-lite-latest"
# More headroom than [1,2,4]: a cold re-extraction (prompt change) fires enough
# requests to trip the model's per-minute quota, and a longer wait clears it.
_BACKOFF = [2, 5, 15]


class GeminiClient:
    def __init__(self, api_key=None, model=PRIMARY_MODEL, fallback=FALLBACK_MODEL):
        api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise SystemExit("GEMINI_API_KEY not set")
        self.client = genai.Client(api_key=api_key)
        self.model = model
        self.fallback = fallback
        self.call_count = 0

    def _contents(self, batch):
        parts = [
            types.Part.from_text(
                text=f"Extract promotions from these {len(batch)} captions. "
                "Return exactly one result object per caption, in this exact order, "
                "and set caption_index to the CAPTION number shown in that caption's header."
            )
        ]
        for idx, inp in enumerate(batch):
            parts.append(
                types.Part.from_text(
                    text=f"\n=== CAPTION {idx} | CAPTURE_DATE: {inp.capture_date} ===\n{inp.text}"
                )
            )
            if inp.image_path:
                # image_path is stored relative to the media root; resolve before reading.
                data = resolve_media(inp.image_path).read_bytes()
                mime = mimetypes.guess_type(inp.image_path)[0] or "image/jpeg"
                parts.append(types.Part.from_bytes(data=data, mime_type=mime))
        return parts

    def _config(self, prompt_text):
        return types.GenerateContentConfig(
            system_instruction=prompt_text,
            response_mime_type="application/json",
            response_schema=BatchResult,
            temperature=0,
        )

    def _generate(self, model, contents, config):
        for attempt in range(len(_BACKOFF) + 1):
            try:
                self.call_count += 1
                return self.client.models.generate_content(
                    model=model, contents=contents, config=config
                )
            except genai.errors.APIError as e:
                code = getattr(e, "code", None)
                if code == 429 and attempt < len(_BACKOFF):
                    log("gemini.rate_limited", model=model, attempt=attempt, backoff_s=_BACKOFF[attempt])
                    time.sleep(_BACKOFF[attempt])
                    continue
                raise

    def extract_batch(self, prompt_text, batch):
        """One API request for a batch. Returns a list of {"index": int, "deals":
        list[dict]}, one per caption the model returned, in returned order. The
        caller verifies index alignment. Falls back to flash-lite on 429."""
        contents = self._contents(batch)
        config = self._config(prompt_text)
        try:
            resp = self._generate(self.model, contents, config)
        except genai.errors.APIError as e:
            if getattr(e, "code", None) == 429:
                resp = self._generate(self.fallback, contents, config)
            else:
                raise
        obj = BatchResult.model_validate_json(resp.text)
        return [
            {"index": cap.caption_index, "deals": [d.model_dump(mode="json") for d in cap.deals]}
            for cap in obj.captions
        ]
