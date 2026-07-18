"use client";

import { Loader2 } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { getSupabase } from "@/lib/supabase/client";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const { error: err } = await getSupabase().auth.resetPasswordForEmail(
        email,
        {
          redirectTo: `${window.location.origin}/auth/callback?next=/reset-password`,
        }
      );
      if (err) throw err;
      setSent(true);
    } catch (err: any) {
      setError(err?.message ?? "Could not send the reset email. Try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto w-full max-w-md px-4 py-14 sm:py-20">
      <div className="card p-7 sm:p-8">
        <h1 className="text-xl font-bold tracking-tight">Reset your password</h1>
        <p className="mt-1.5 text-sm text-muted">
          Enter your account email and we&apos;ll send you a secure reset link.
        </p>

        {sent ? (
          <div className="mt-6 rounded-lg border border-teal/40 bg-teal-soft p-4 text-sm text-teal">
            If an account exists for <span className="font-semibold">{email}</span>,
            a reset link is on its way. Check your inbox (and spam folder).
          </div>
        ) : (
          <form onSubmit={submit} className="mt-6 space-y-4">
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
            {error && <p className="text-sm text-red-300">{error}</p>}
            <button type="submit" disabled={loading} className="btn-accent w-full">
              {loading && <Loader2 className="animate-spin" size={15} />}
              Send Reset Link
            </button>
          </form>
        )}

        <p className="mt-6 text-center text-sm text-muted">
          Remembered it?{" "}
          <Link href="/login" className="text-accent">Back to sign in</Link>
        </p>
      </div>
    </div>
  );
}
