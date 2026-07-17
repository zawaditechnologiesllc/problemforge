import { Lock } from "lucide-react";
import Link from "next/link";

const PLACEHOLDER_LINES = [
  "w-11/12", "w-full", "w-9/12", "w-10/12", "w-full", "w-8/12", "w-11/12", "w-7/12",
];

export function LockedPanel({ message }: { message: string }) {
  return (
    <div className="relative overflow-hidden rounded-lg">
      {/* Decorative placeholder text, blurred — real content never reaches the client */}
      <div aria-hidden className="select-none space-y-2.5 p-1 blur-[6px]">
        {PLACEHOLDER_LINES.map((width, index) => (
          <div key={index} className={`h-3.5 rounded bg-raised ${width}`} />
        ))}
      </div>
      <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 bg-surface/60 px-6 text-center">
        <span className="flex h-10 w-10 items-center justify-center rounded-full border border-accent/40 bg-accent-soft text-accent">
          <Lock size={17} />
        </span>
        <p className="max-w-sm text-sm text-muted">{message}</p>
        <Link href="/pricing" className="btn-accent">
          Upgrade to Unlock
        </Link>
      </div>
    </div>
  );
}
