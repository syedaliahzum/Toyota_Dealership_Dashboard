import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const PROTECTED_PREFIXES = ["/manager-dashboard"];

export function proxy(req: NextRequest) {
  const { nextUrl, cookies } = req;
  const pathname = nextUrl.pathname;

  const needsAuth = PROTECTED_PREFIXES.some((p) => pathname.startsWith(p));
  if (!needsAuth) return NextResponse.next();

  const session = cookies.get("auth_session")?.value;
  const expStr = cookies.get("auth_exp")?.value;
  const banned = cookies.get("auth_banned")?.value === "1";

  const signinUrl = new URL("/", req.url); // home is the signin page

  if (banned) {
    signinUrl.searchParams.set("banned", "1");
    return NextResponse.redirect(signinUrl);
  }

  if (!session || !expStr) {
    signinUrl.searchParams.set("expired", "1");
    return NextResponse.redirect(signinUrl);
  }

  const now = Math.floor(Date.now() / 1000);
  const exp = Number(expStr || 0);

  if (Number.isNaN(exp) || now >= exp) {
    // Expired: clear session and permanently ban further logins with same password
    const res = NextResponse.redirect(signinUrl);
    res.cookies.set("auth_session", "", { path: "/", maxAge: 0 });
    res.cookies.set("auth_exp", "", { path: "/", maxAge: 0 });
    res.cookies.set("auth_banned", "1", {
      path: "/",
      httpOnly: false,
      sameSite: "lax",
      maxAge: 10 * 365 * 24 * 60 * 60,
    });
    signinUrl.searchParams.set("expired", "1");
    return res;
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/manager-dashboard/:path*"],
};
