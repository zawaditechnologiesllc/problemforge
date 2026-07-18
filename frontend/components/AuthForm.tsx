"use client";

import { Loader2 } from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import { PasswordInput } from "@/components/PasswordInput";
import { getSupabase } from "@/lib/supabase/client";

function siteUrl() {
  if (typeof window !== "undefined") return window.location.origin;
  return process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000";
}

export function AuthForm({ mode }: { mode: "login" | "signup" }) {
  const router = useRouter();
  const params = useSearchParams();
  const next = params.get("next") ?? "/account";

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  // Surface auth-callback errors (expired confirmation links etc.)
  const [error, setError] = useState<string | null>(params.get("error"));
  const [notice, setNotice] = useState<string | null>(null);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    setNotice(null);
    const supabase = getSupabase();
    try {
      if (mode === "login") {
        const { error: err } = await supabase.auth.signInWithPassword({
          email,
          password,
        });
        if (err) throw err;
        router.push(next);
        router.refresh();
      } else {
        const { data, error: err } = await supabase.auth.signUp({
          email,
          password,
          options: { emailRedirectTo: `${siteUrl()}/auth/callback?next=${next}` },
        });
        if (err) throw err;
        if (data.session) {
          router.push(next);
          router.refresh();
        } else {
          setNotice("Check your email for a confirmation link to finish signing up.");
        }
      }
    } catch (err: any) {
      setError(err?.message ?? "Something went wrong. Try again.");
    } finally {
      setLoading(false);
    }
  }

  async function signInWithGoogle() {
    setError(null);
    const { error: err } = await getSupabase().auth.signInWithOAuth({
      provider: "google",
      options: {
        redirectTo: `${siteUrl()}/auth/callback?next=${next}`,
      },
    });
    if (err) setError(err.message);
  }

  return (
    <div className="mx-auto w-full max-w-md px-4 py-14 sm:py-20">
      <div className="card p-7 sm:p-8">
        <h1 className="text-xl font-bold tracking-tight">
          {mode === "login" ? "Welcome back" : "Create your account"}
        </h1>
        <p className="mt-1.5 text-sm text-muted">
          {mode === "login"
            ? "Sign in to your ProblemForge account."
            : "Free forever plan — no card required."}
        </p>

        <button onClick={signInWithGoogle} className="btn-ghost mt-6 w-full">
          <svg width="16" height="16" viewBox="0 0 24 24" aria-hidden>
            <path
              fill="currentColor"
              d="M21.35 11.1H12v2.9h5.35c-.5 2.5-2.6 4.3-5.35 4.3a5.8 5.8 0 1 1 0-11.6c1.5 0 2.8.55 3.85 1.45l2.15-2.15A8.8 8.8 0 1 0 12 20.8c4.4 0 8.75-3.2 8.75-8.8 0-.3-.15-.6-.4-.9Z"
            />
          </svg>
          Continue with Google
        </button>

        <div className="my-6 flex items-center gap-3 text-xs text-muted">
          <span className="h-px flex-1 bg-edge" /> or <span className="h-px flex-1 bg-edge" />
        </div>

        <form onSubmit={submit} className="space-y-4">
          <div>
            <label className="mb-1.5 block text-xs font-medium text-muted">Email</label>
            <input
              type="email"
              required
              className="input"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="you@example.com"
            />
          </div>
          <div>
            <div className="mb-1.5 flex items-center justify-between">
              <label className="block text-xs font-medium text-muted">Password</label>
              {mode === "login" && (
                <Link href="/forgot-password" className="text-xs text-accent">
                  Forgot password?
                </Link>
              )}
            </div>
            <PasswordInput
              value={password}
              onChange={setPassword}
              placeholder={mode === "signup" ? "At least 8 characters" : "••••••••"}
              autoComplete={mode === "signup" ? "new-password" : "current-password"}
            />
          </div>

          {error && <p className="text-sm text-red-300">{error}</p>}
          {notice && <p className="text-sm text-teal">{notice}</p>}

          <button type="submit" disabled={loading} className="btn-accent w-full">
            {loading && <Loader2 className="animate-spin" size={15} />}
            {mode === "login" ? "Sign In" : "Create Account"}
          </button>
        </form>

        {mode === "signup" && (
          <p className="mt-4 text-center text-xs leading-relaxed text-muted">
            By creating an account you agree to the{" "}
            <Link href="/terms" className="text-accent">Terms of Service</Link>{" "}
            and <Link href="/privacy" className="text-accent">Privacy Policy</Link>.
          </p>
        )}

        <p className="mt-6 text-center text-sm text-muted">
          {mode === "login" ? (
            <>
              New to ProblemForge?{" "}
              <Link href="/signup" className="text-accent">Create an account</Link>
            </>
          ) : (
            <>
              Already have an account?{" "}
              <Link href="/login" className="text-accent">Sign in</Link>
            </>
          )}
        </p>
      </div>
    </div>
  );
}
