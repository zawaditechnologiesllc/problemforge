"use client";

import { Download, FileText, Loader2, RefreshCw } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  ftoCheckout,
  getFtoDownload,
  listFtoReports,
  retryFtoReport,
} from "@/lib/api";
import type { FtoReport } from "@/lib/types";
import clsx from "clsx";

const statusStyles: Record<FtoReport["status"], string> = {
  pending_payment: "border-edge text-muted",
  queued: "border-accent/40 bg-accent-soft text-accent",
  processing: "border-accent/40 bg-accent-soft text-accent",
  ready: "border-teal/40 bg-teal-soft text-teal",
  failed: "border-red-400/40 bg-red-400/10 text-red-300",
};

const statusLabels: Record<FtoReport["status"], string> = {
  pending_payment: "Awaiting payment",
  queued: "Queued",
  processing: "Generating",
  ready: "Ready",
  failed: "Failed",
};

export function FtoPanel({ justPaid }: { justPaid: boolean }) {
  const [reports, setReports] = useState<FtoReport[]>([]);
  const [patentNumber, setPatentNumber] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const pollUntil = useRef<number>(0);

  const refresh = useCallback(() => {
    listFtoReports()
      .then((data) => setReports(data.items))
      .catch(() => undefined);
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  // Reports generate asynchronously after payment — poll while any are in
  // flight (or right after returning from checkout), capped at 3 minutes.
  useEffect(() => {
    const active = reports.some((r) =>
      ["queued", "processing", "pending_payment"].includes(r.status)
    );
    if (justPaid || active) pollUntil.current = Date.now() + 3 * 60 * 1000;
    if (Date.now() >= pollUntil.current) return;
    const timer = setInterval(() => {
      if (Date.now() >= pollUntil.current) {
        clearInterval(timer);
        return;
      }
      refresh();
    }, 5000);
    return () => clearInterval(timer);
  }, [justPaid, reports, refresh]);

  async function order(event: React.FormEvent) {
    event.preventDefault();
    if (!patentNumber.trim() || busy) return;
    setBusy("order");
    setError(null);
    try {
      const { url } = await ftoCheckout({ patent_number: patentNumber.trim() });
      window.location.href = url;
    } catch (err: any) {
      setError(err?.message ?? "Could not start checkout");
      setBusy(null);
    }
  }

  async function download(id: string) {
    setBusy(`dl-${id}`);
    setError(null);
    try {
      const { url } = await getFtoDownload(id);
      window.open(url, "_blank", "noopener");
    } catch (err: any) {
      setError(err?.message ?? "Download failed");
    } finally {
      setBusy(null);
    }
  }

  async function retry(id: string) {
    setBusy(`retry-${id}`);
    setError(null);
    try {
      await retryFtoReport(id);
      refresh();
    } catch (err: any) {
      setError(err?.message ?? "Retry failed");
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="space-y-6">
      {justPaid && (
        <div className="card border-teal/40 bg-teal-soft p-4 text-sm text-teal">
          Payment received — your report is being generated and will appear
          below shortly (usually under a minute).
        </div>
      )}

      <div className="card p-6">
        <h2 className="flex items-center gap-2.5 font-semibold">
          <FileText size={18} className="text-teal" />
          Freedom-to-Operate Report — $99 one-time
        </h2>
        <p className="mt-2 text-sm leading-relaxed text-muted">
          A PDF report re-verifying a patent&apos;s expired status before you
          build on it: statutory-term math, recorded legal status, a live USPTO
          re-check, and a plain-language analysis. An AI-generated
          informational summary — <span className="text-ink">not legal advice</span>.
        </p>
        <form onSubmit={order} className="mt-5 flex flex-col gap-3 sm:flex-row">
          <input
            className="input sm:max-w-xs"
            placeholder="Patent number, e.g. US7156808B2"
            value={patentNumber}
            onChange={(event) => setPatentNumber(event.target.value)}
            aria-label="Patent number"
          />
          <button
            type="submit"
            disabled={busy === "order" || !patentNumber.trim()}
            className="btn-accent"
          >
            {busy === "order" && <Loader2 className="animate-spin" size={15} />}
            Order Report — $99
          </button>
        </form>
        <p className="mt-2.5 text-xs text-muted">
          Tip: you can also order straight from any blueprint page.
        </p>
      </div>

      {error && (
        <div className="card border-red-400/30 p-4 text-sm text-red-300">{error}</div>
      )}

      <div>
        <h3 className="mb-3 font-semibold">Your reports</h3>
        {reports.length === 0 ? (
          <div className="card p-8 text-center text-sm text-muted">
            No reports yet.
          </div>
        ) : (
          <div className="card divide-y divide-edge">
            {reports.map((report) => (
              <div
                key={report.id}
                className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between"
              >
                <div className="min-w-0">
                  <p className="font-mono text-sm font-semibold">
                    {report.patent_number}
                  </p>
                  <p className="mt-1 text-xs text-muted">
                    Ordered {new Date(report.created_at).toLocaleDateString()}
                    {report.status === "failed" && report.error
                      ? ` — ${report.error.slice(0, 120)}`
                      : ""}
                  </p>
                </div>
                <div className="flex flex-none items-center gap-3">
                  <span
                    className={clsx(
                      "rounded-full border px-2.5 py-1 text-[11px] font-semibold",
                      statusStyles[report.status]
                    )}
                  >
                    {(report.status === "queued" || report.status === "processing") && (
                      <Loader2 className="mr-1 inline animate-spin" size={10} />
                    )}
                    {statusLabels[report.status]}
                  </span>
                  {report.status === "ready" && (
                    <button
                      className="btn-ghost px-3 py-1.5 text-xs"
                      disabled={busy === `dl-${report.id}`}
                      onClick={() => download(report.id)}
                    >
                      <Download size={13} /> PDF
                    </button>
                  )}
                  {report.status === "failed" && (
                    <button
                      className="btn-ghost px-3 py-1.5 text-xs"
                      disabled={busy === `retry-${report.id}`}
                      onClick={() => retry(report.id)}
                    >
                      <RefreshCw size={13} /> Retry
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <p className="text-xs leading-relaxed text-muted">
        Reports are AI-generated informational summaries, not legal advice or a
        guarantee of freedom to operate. Patent statuses can be contested,
        corrected, or reinstated — consult a qualified patent attorney before
        making commercial decisions.
      </p>
    </div>
  );
}
