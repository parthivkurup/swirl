import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

// The paths the Cloudflare Tunnel publishes, mirroring ops/cloudflared/config.yml.
const PUBLIC = [/^\/$/, /^\/submit\/?$/, /^\/api\/submit\/?$/, /^\/_next\//];

// Defence in depth for the tunnel allowlist.
//
// The ingress rules in ops/cloudflared/config.yml are the primary control and
// they are what stops a request ever reaching this process. This exists so the
// guarantee does not depend on a YAML file staying correct: if the tunnel is
// ever misconfigured, restarted with `--url` (a quick tunnel ignores ingress
// rules entirely), or pointed at this origin by anything else, /review, /login,
// /api/image and /api/deals still refuse to answer.
//
// Cloudflare's edge always sets cf-ray on requests it forwards. A request with
// no such header did not come through Cloudflare, which is the localhost case,
// and is passed through untouched. The header cannot be used to gain access,
// only to lose it, so a spoofed one is harmless.
export function middleware(req: NextRequest) {
  const viaCloudflare = req.headers.has("cf-ray") || req.headers.has("cf-connecting-ip");
  if (!viaCloudflare) return NextResponse.next();

  if (PUBLIC.some((re) => re.test(req.nextUrl.pathname))) return NextResponse.next();

  // 404 rather than 403: a probe learns nothing about what exists here.
  return new NextResponse("Not found", { status: 404 });
}

export const config = { matcher: "/:path*" };
