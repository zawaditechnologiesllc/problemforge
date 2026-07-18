"use client";

import { Loader2 } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { PasswordInput } from "@/components/PasswordInput";
import { getSupabase } from "@/lib/supabase/client";

export default function ResetPasswordPage() {
  const router = useRouter();
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasSession, setHasSession] = useState<boolean | null>(null);

  // The reset email lands on /auth/callback which exchanges the recovery code
  // for a session, then redirects here — so a valid visit has a session.
  useEffect(() => {
    getSupabase()
      .auth.getSession()
      .then(({ data }) => setHasSession(!!data.session))
      .catch(() => setHasSession(false));
  }, []);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (password !== confirm) {
      setError("Passwords do not match.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const { error: err } = await getSupabase().auth.updateUser({ password });
      if (err) throw err;
      router.push("/account");
      router.refresh();
    } catch (err: any) {
      setError(err?.message ?? "Could not update the password. Try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto w-full max-w-md px-4 py-14 sm:py-20">
      <div className="card p-7 sm:p-8">
        <h1 className="text-xl font-bold tracking-tight">Choose a new password</h1>

        {hasSession === null ? (
          <div className="mt-6 flex justify-center py-6 text-muted">
            <Loader2 className="animate-spin" size={20} />
          </div>
        ) : hasSession ? (
          <form onSubmit={submit} className="mt-6 space-y-4">
            <div>
              <label className="mb-1.5 block text-xs font-medium text-muted">
                New password
              </label>
              <PasswordInput
                value={password}
                onChange={setPassword}
                placeholder="At least 8 characters"
                autoComplete="new-password"
              />
            </div>
            <div>
              <label className="mb-1.5 block text-xs font-medium text-muted">
                Confirm new password
              </label>
              <PasswordInput
                value={confirm}
                onChange={setConfirm}
                placeholder="Repeat the password"
                autoComplete="new-password"
              />
            </div>
            {error && <p className="text-sm text-red-300">{error}</p>}
            <button type="submit" disabled={loading} className="btn-accent w-full">
              {loading && <Loader2 className="animate-spin" size={15} />}
              Update Password
            </button>
          </form>
        ) : (
          <div className="mt-6 space-y-4">
            <p className="text-sm text-muted">
              This reset link is invalid or has expired. Request a fresh one and
              use it within an hour.
            </p>
            <Link href="/forgot-password" className="btn-accent w-full">
              Request a New Link
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}
