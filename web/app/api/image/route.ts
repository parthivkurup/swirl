import { existsSync, readFileSync } from "node:fs";

import { NextRequest, NextResponse } from "next/server";

import { isAuthed } from "@/lib/auth";
import { pool } from "@/lib/db";
import { resolveMedia } from "@/lib/media";

// Serves a capture's source image to the review queue. Admin only: submission
// photos are behind the reviewer surface. Only paths recorded in
// raw_captures.image_path are served, so an arbitrary local file cannot be read.
export async function GET(req: NextRequest) {
  if (!isAuthed()) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }
  const path = req.nextUrl.searchParams.get("path");
  if (!path) return NextResponse.json({ error: "no path" }, { status: 400 });

  const { rows } = await pool.query(
    `select 1 from raw_captures where image_path = $1 limit 1`,
    [path]
  );
  // image_path is stored relative to the media root; resolve before touching disk.
  const file = resolveMedia(path);
  if (rows.length === 0 || !file || !existsSync(file)) {
    return NextResponse.json({ error: "not found" }, { status: 404 });
  }

  const data = readFileSync(file);
  const ext = path.split(".").pop()?.toLowerCase();
  const type = ext === "png" ? "image/png" : ext === "webp" ? "image/webp" : "image/jpeg";
  return new NextResponse(data, { headers: { "content-type": type } });
}
