import { NextRequest, NextResponse } from "next/server";
import { hasValidWebAuth, webAuthRequired } from "./lib/api-guard";

export function middleware(request: NextRequest) {
  if (!webAuthRequired()) return NextResponse.next();
  if (hasValidWebAuth(request)) return NextResponse.next();

  return new NextResponse("Authentication required", {
    status: 401,
    headers: {
      "WWW-Authenticate": 'Basic realm="SoloOS Mission Control"',
    },
  });
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
