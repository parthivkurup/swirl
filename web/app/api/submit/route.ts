import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import { mkdir, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import crypto from "node:crypto";

import { NextRequest, NextResponse } from "next/server";

const MAX_BYTES = 10 * 1024 * 1024;
const RATE_MAX = 5;
const RATE_WINDOW_MS = 10 * 60 * 1000;

// Simple in-process rate limit. Resets on restart; fine at this stage.
//
// The map is keyed by a salted digest, never by the address itself. A bare
// sha256 of an IPv4 address is not anonymisation: the whole space is 2^32 and
// reverses in seconds on a laptop. The salt is random per process and never
// leaves memory, so the key cannot be taken back to an address, and the same
// visitor does not produce the same key across restarts.
const IP_SALT = crypto.randomBytes(32);
const hits = new Map<string, number[]>();

function ipKey(ip: string) {
  return crypto.createHash("sha256").update(IP_SALT).update(ip).digest("hex");
}

// Drop expired timestamps and forget any key whose window has emptied, so a
// visitor's entry does not outlive the ten minutes it exists to enforce.
function sweep(now: number) {
  for (const [key, times] of hits) {
    const live = times.filter((t) => now - t < RATE_WINDOW_MS);
    if (live.length === 0) hits.delete(key);
    else if (live.length !== times.length) hits.set(key, live);
  }
}

function rateOk(key: string) {
  const now = Date.now();
  sweep(now);
  const times = hits.get(key) ?? [];
  if (times.length >= RATE_MAX) return false;
  times.push(now);
  hits.set(key, times);
  return true;
}

// Validate by magic bytes, not just extension.
function sniff(b: Buffer): "jpg" | "png" | "heic" | null {
  if (b.length > 3 && b[0] === 0xff && b[1] === 0xd8 && b[2] === 0xff) return "jpg";
  if (b.length > 8 && b[0] === 0x89 && b[1] === 0x50 && b[2] === 0x4e && b[3] === 0x47) return "png";
  if (b.length > 12 && b.subarray(4, 8).toString("ascii") === "ftyp") {
    const brand = b.subarray(8, 12).toString("ascii");
    if (["heic", "heix", "mif1", "heif", "hevc", "msf1"].includes(brand)) return "heic";
  }
  return null;
}

function repoRoot() {
  const cwd = process.cwd();
  for (const cand of [path.resolve(cwd, ".."), cwd, path.resolve(cwd, "..", "..")]) {
    if (existsSync(path.join(cand, ".venv", "bin", "python"))) return cand;
  }
  return path.resolve(cwd, "..");
}

export async function POST(req: NextRequest) {
  const ip = (req.headers.get("x-forwarded-for") ?? "local").split(",")[0].trim();
  if (!rateOk(ipKey(ip))) {
    return NextResponse.json({ error: "Too many submissions. Please try again later." }, { status: 429 });
  }

  // A request with no multipart body makes formData() throw. Unreachable from the
  // form, but this endpoint is on the public internet now and gets probed, and a
  // malformed POST is the client's mistake, not a server fault.
  let form: FormData;
  try {
    form = await req.formData();
  } catch {
    return NextResponse.json({ error: "Malformed submission." }, { status: 400 });
  }

  const file = form.get("photo");
  if (!(file instanceof File)) {
    return NextResponse.json({ error: "A photo is required." }, { status: 400 });
  }
  if (file.size > MAX_BYTES) {
    return NextResponse.json({ error: "Photo must be 10MB or smaller." }, { status: 400 });
  }
  const buf = Buffer.from(await file.arrayBuffer());
  const kind = sniff(buf);
  if (!kind) {
    return NextResponse.json({ error: "Only jpg, png or heic images are accepted." }, { status: 400 });
  }

  const text = String(form.get("text") ?? "").trim();
  // The shop name travels as its own argument, not concatenated into the caption.
  // A labelled form field is not caption prose, so the extractor prompt rightly
  // refuses to read "Store: X" as a store_hint; ingest.submit stores it in
  // raw_captures.submitted_store and post-processing uses it directly.
  const store = String(form.get("store") ?? "").trim();

  const dir = path.join(tmpdir(), "froyo-submit");
  await mkdir(dir, { recursive: true });
  const tmp = path.join(dir, `${crypto.randomUUID()}.${kind}`);
  await writeFile(tmp, buf);

  // Reuse the manual ingestion path via ingest.submit (sanitizes EXIF, inserts a
  // user_submission raw_capture). Extraction runs later on the schedule.
  const repo = repoRoot();
  const py = path.join(repo, ".venv", "bin", "python");
  const args = ["-m", "ingest.submit", "--image", tmp];
  if (text) args.push("--stdin");
  if (store) args.push("--store", store);

  const ok = await new Promise<boolean>((resolve) => {
    const p = spawn(py, args, { cwd: repo });
    if (text) p.stdin.write(text);
    p.stdin.end();
    let err = "";
    p.stderr.on("data", (d) => (err += d));
    p.on("error", () => resolve(false));
    p.on("close", (code) => {
      if (code !== 0) console.error("ingest.submit failed:", err);
      resolve(code === 0);
    });
  });

  if (!ok) {
    return NextResponse.json({ error: "Could not process that image." }, { status: 500 });
  }
  return NextResponse.json({ ok: true, message: "Thanks! Your submission is pending review." });
}
