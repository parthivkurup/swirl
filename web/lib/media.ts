import path from "node:path";

// Mirrors ingest/media.py. raw_captures.image_path is stored relative to the media
// root ("submissions/<hash>.jpg"), so a row never depends on where this checkout
// sits. MEDIA_ROOT overrides the default of <repo>/media.
export function mediaRoot(): string {
  const env = (process.env.MEDIA_ROOT ?? "").trim();
  if (env) return path.resolve(env);
  // The Next app lives in web/, so the repo root is one level up from cwd.
  return path.resolve(process.cwd(), "..", "media");
}

// Resolve a stored image_path to a real file. Absolute values are legacy rows
// written before paths became relative. Returns null when a relative path would
// escape the media root, which the database allowlist should already prevent but
// which is too cheap a check to skip on a path that reads a file.
export function resolveMedia(stored: string): string | null {
  if (path.isAbsolute(stored)) return stored;
  const root = mediaRoot();
  const full = path.resolve(root, stored);
  return full === root || full.startsWith(root + path.sep) ? full : null;
}
