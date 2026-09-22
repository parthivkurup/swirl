import { NextRequest, NextResponse } from "next/server";

import { isAuthed } from "@/lib/auth";
import { searchDeals } from "@/lib/deals";

// Deal search for the "duplicate of" picker. Admin-only, like the mutation routes.
export async function GET(req: NextRequest) {
  if (!isAuthed()) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }
  const q = (req.nextUrl.searchParams.get("q") ?? "").trim();
  if (!q) {
    return NextResponse.json({ deals: [] });
  }
  const deals = await searchDeals(q);
  return NextResponse.json({ deals });
}
