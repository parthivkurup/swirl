import crypto from "node:crypto";

import { cookies } from "next/headers";

import { MAX_AGE_S, makeToken, verifyToken } from "./session";

export const SESSION_COOKIE = "froyo_admin";

export function passwordOk(input: string): boolean {
  const pw = process.env.ADMIN_PASSWORD;
  if (!pw) return false;
  const a = crypto.createHash("sha256").update(input).digest();
  const b = crypto.createHash("sha256").update(pw).digest();
  return crypto.timingSafeEqual(a, b);
}

export function makeSession(): string | null {
  return makeToken(Date.now());
}

export function isAuthed(): boolean {
  const raw = cookies().get(SESSION_COOKIE)?.value;
  return verifyToken(raw, Date.now());
}

export function cookieOptions() {
  return {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax" as const,
    path: "/",
    maxAge: MAX_AGE_S,
  };
}
