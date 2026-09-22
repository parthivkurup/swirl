import { NextRequest, NextResponse } from "next/server";

import { SESSION_COOKIE, cookieOptions, makeSession, passwordOk } from "@/lib/auth";

export async function POST(req: NextRequest) {
  const body = await req.json().catch(() => ({}));
  const password = String(body.password ?? "");
  if (!passwordOk(password)) {
    return NextResponse.json({ error: "Incorrect password." }, { status: 401 });
  }
  const value = makeSession();
  if (!value) {
    return NextResponse.json({ error: "SESSION_SECRET is not configured." }, { status: 500 });
  }
  const res = NextResponse.json({ ok: true });
  res.cookies.set(SESSION_COOKIE, value, cookieOptions());
  return res;
}
