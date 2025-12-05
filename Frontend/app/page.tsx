"use client";

import { Suspense, useEffect, useMemo, useState } from "react";
import Image from "next/image";
import { useRouter, useSearchParams } from "next/navigation";

/** ===== Hardcoded credentials ===== */
const VALID_EMAIL = "manager@toyotagt.com.pk";
const VALID_PASS = "123Toyota";
const DAYS_30_SEC = 30 * 24 * 60 * 60;

/** Cookie helpers */
function setCookie(name: string, value: string, maxAgeSeconds?: number) {
  const parts = [`${name}=${encodeURIComponent(value)}`, "Path=/", "SameSite=Lax"];
  if (typeof window !== "undefined" && location.protocol === "https:") parts.push("Secure");
  if (maxAgeSeconds) parts.push(`Max-Age=${maxAgeSeconds}`);
  document.cookie = parts.join("; ");
}
function deleteCookie(name: string) {
  document.cookie = `${name}=; Path=/; Max-Age=0; SameSite=Lax`;
}
function readCookie(name: string) {
  if (typeof document === "undefined") return null;
  const m = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return m ? decodeURIComponent(m[1]) : null;
}

export default function Page() {
  return (
    <Suspense>
      <SignInPage />
    </Suspense>
  );
}
function SignInPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const expired = searchParams.get("expired") === "1";
  const bannedParam = searchParams.get("banned") === "1";
  const bannedCookie = useMemo(() => readCookie("auth_banned") === "1", []);

  useEffect(() => {
    if (expired) setError("Your access period has expired. Contact admin for a new password.");
    if (bannedParam || bannedCookie)
      setError("Login disabled. You cannot use this password again.");
  }, [expired, bannedParam, bannedCookie]);

  async function onSignIn() {
    setError("");

    if (!username || !password) {
      setError("Please enter both username and password.");
      return;
    }

    // Hardcoded check
    const isValid =
      username.trim().toLowerCase() === VALID_EMAIL && password === VALID_PASS;

    // Banned after expiry — don't let them in ever again with same password
    const isBanned = readCookie("auth_banned") === "1";
    if (isBanned) {
      setError("Login disabled. You cannot use this password again.");
      return;
    }

    if (!isValid) {
      setError("Invalid credentials.");
      return;
    }

    setSubmitting(true);
    try {
      const now = Math.floor(Date.now() / 1000);
      const existingExp = readCookie("auth_exp");
      let exp = existingExp ? parseInt(existingExp, 10) : now + DAYS_30_SEC;

      if (!existingExp) {
        // First successful login → set absolute expiry at now + 30 days
        setCookie("auth_exp", String(exp), DAYS_30_SEC);
      } else if (Number.isFinite(exp) && now >= exp) {
        // If already expired for some reason, enforce ban
        setCookie("auth_banned", "1", 10 * 365 * 24 * 60 * 60);
        deleteCookie("auth_session");
        deleteCookie("auth_exp");
        setError("Login disabled. You cannot use this password again.");
        setSubmitting(false);
        return;
      }

      // Active session cookie that cannot extend beyond absolute exp
      setCookie("auth_session", "1", Math.max(1, exp - now));
      deleteCookie("auth_banned"); // ensure it’s off during valid period

      // Redirect to dashboard
      router.replace("/manager-dashboard");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="min-h-screen bg-white text-zinc-900 dark:bg-black dark:text-white"> {/* This main tag already handles light/dark for overall page */}
      <div className="grid min-h-screen grid-cols-1 md:grid-cols-2">
        {/* LEFT: background image + titles (unchanged styling) */}
        <section className="relative hidden md:block">
          <Image
            src="/toyota.jpg"
            alt="Toyota car"
            fill
            className="object-cover opacity-50"
            priority
          />
          <div className="absolute inset-0 bg-black/60 backdrop-blur-[1px] dark:bg-black/40" />
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="px-8 text-center">
              <Image
                src="/toyota-logo.png"
                alt="Toyota G.T Motors logo"
                width={120}
                height={120}
                className="mx-auto mb-3"
                priority
              />

              <p className="mt-2 text-sm uppercase tracking-[0.25em] text-zinc-200">
                Manager Admin Panel
              </p>
              <br />
              <h1 className="text-4xl font-extrabold tracking-wide text-white md:text-5xl">
                TOYOTA
              </h1>
              <h1 className="text-2xl font-bold tracking-wide md:text-3xl text-[#ef4444]">
                G.T MOTORS
              </h1>
            </div>
          </div>
        </section>

        {/* RIGHT: sign-in panel (unchanged styling) */}
        <section className="flex items-center justify-center bg-white dark:bg-black px-6 py-12">
          <div className="w-full max-w-md">
            <h2 className="text-2xl font-semibold">SIGN IN</h2>
            <div className="mt-1 h-0.5 w-10 bg-red-500" />

            <p className="mt-6 text-sm text-zinc-500 dark:text-zinc-400">
              Please enter your username and password below to signin
            </p>

            {/* Username */}
            <label className="mt-6 block text-sm text-zinc-800 dark:text-zinc-300">Username</label>
            <div className="relative mt-2">
              <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2">
                {/* user icon (red) */}
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden>
                  <path d="M20 21a8 8 0 1 0-16 0" stroke="#ef4444" strokeWidth="1.8" />
                  <circle cx="12" cy="7" r="4" stroke="#ef4444" strokeWidth="1.8" />
                </svg>
              </span>
              <input
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="Username"
                className="w-full rounded-none border border-zinc-300 bg-transparent px-11 py-3 text-sm outline-none placeholder:text-zinc-400 focus:border-zinc-500 dark:border-zinc-600 dark:placeholder:text-zinc-500 dark:focus:border-zinc-400"
                autoComplete="username"
              />
            </div>

            {/* Password */}
            <label className="mt-5 block text-sm text-zinc-800 dark:text-zinc-300">Password</label>
            <div className="relative mt-2">
              <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2">
                {/* lock icon (red) */}
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden>
                  <rect x="3" y="10" width="18" height="11" rx="2" stroke="#ef4444" strokeWidth="1.8" />
                  <path d="M7 10V8a5 5 0 0 1 10 0v2" stroke="#ef4444" strokeWidth="1.8" />
                </svg>
              </span>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Password"
                className="w-full rounded-none border border-zinc-300 bg-transparent px-11 py-3 text-sm outline-none placeholder:text-zinc-400 focus:border-zinc-500 dark:border-zinc-600 dark:placeholder:text-zinc-500 dark:focus:border-zinc-400"
                autoComplete="current-password"
              />
            </div>

            {/* Error message (minimal, fits your design) */}
            {error && (
              <p className="mt-3 text-sm text-red-400">{error}</p>
            )}

            {/* Forgot */}
            {/*<button
              type="button"
              className="mt-3 text-left text-xs text-zinc-500 hover:text-zinc-700 dark:text-zinc-400 dark:hover:text-zinc-200"
            >
              Forgot Password?
            </button>*/}

            {/* Submit */}
            <button
              type="button"
              onClick={onSignIn}
              disabled={submitting}
              className="mt-6 w-full rounded-none border border-zinc-300 bg-[#ef4444] px-6 py-3 font-semibold tracking-wide text-zinc-800 hover:bg-zinc-200 disabled:opacity-60 dark:border-zinc-600 dark:bg-zinc-900 dark:text-white dark:hover:bg-zinc-800"
            >
              {submitting ? "Signing in..." : "SIGN IN"}
            </button>
          </div>
        </section>
      </div>
    </main>
  );
}
