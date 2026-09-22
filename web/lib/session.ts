import crypto from "node:crypto";

// Pure session-token logic, no next/headers, so it is unit-testable. The token
// is `<iat>.<hmac>` where iat is the issued-at time in ms and the HMAC is over
// iat with SESSION_SECRET (separate from ADMIN_PASSWORD). Sessions older than
// MAX_AGE_MS are rejected, and rotating SESSION_SECRET invalidates all sessions.
const MAX_AGE_MS = 7 * 24 * 60 * 60 * 1000;
const SKEW_MS = 60 * 1000;

export const MAX_AGE_S = Math.floor(MAX_AGE_MS / 1000);

function secret(): string | null {
  return process.env.SESSION_SECRET || null;
}

function sign(payload: string): string {
  return crypto.createHmac("sha256", secret() as string).update(payload).digest("hex");
}

export function makeToken(iatMs: number): string | null {
  if (!secret()) return null;
  const iat = String(iatMs);
  return `${iat}.${sign(iat)}`;
}

export function verifyToken(raw: string | undefined, nowMs: number): boolean {
  if (!secret() || !raw) return false;
  const dot = raw.lastIndexOf(".");
  if (dot <= 0) return false;
  const iat = raw.slice(0, dot);
  const mac = raw.slice(dot + 1);
  const expected = sign(iat);
  const a = Buffer.from(mac);
  const b = Buffer.from(expected);
  if (a.length !== b.length || !crypto.timingSafeEqual(a, b)) return false;
  const ts = Number(iat);
  if (!Number.isFinite(ts)) return false;
  if (nowMs - ts > MAX_AGE_MS) return false; // expired
  if (ts - nowMs > SKEW_MS) return false; // issued in the future
  return true;
}
