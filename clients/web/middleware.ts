import { NextResponse } from "next/server";
import { getToken } from "next-auth/jwt";
import type { NextRequest } from "next/server";

export async function middleware(req: NextRequest) {
  const token = await getToken({ req });
  const { pathname } = req.nextUrl;

  // Allow public paths
  if (
    pathname.startsWith("/login") ||
    pathname.startsWith("/pending") ||
    pathname.startsWith("/api/auth")
  ) {
    return NextResponse.next();
  }

  // Not logged in → go to login
  if (!token) {
    return NextResponse.redirect(new URL("/login", req.url));
  }

  // Logged in but not approved → go to pending
  if (!token.approved) {
    return NextResponse.redirect(new URL("/pending", req.url));
  }

  // Inject API key for backend proxy requests
  if (pathname.startsWith("/api/")) {
    const requestHeaders = new Headers(req.headers);
    requestHeaders.set("X-API-Key", process.env.SARA_API_KEY ?? "");
    return NextResponse.next({
      request: { headers: requestHeaders },
    });
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
