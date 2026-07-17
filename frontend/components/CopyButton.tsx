"use client";

import { Check, Copy } from "lucide-react";
import { useState } from "react";
import clsx from "clsx";

export function CopyButton({
  text,
  label = "Copy Master Prompt",
  onCopied,
  className,
}: {
  text: string;
  label?: string;
  onCopied?: () => void;
  className?: string;
}) {
  const [copied, setCopied] = useState(false);

  async function copy() {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      onCopied?.();
      setTimeout(() => setCopied(false), 2500);
    } catch {
      // Clipboard unavailable (permissions/http): fall back to selection
      window.prompt("Copy the prompt below:", text);
    }
  }

  return (
    <button type="button" onClick={copy} className={clsx("btn-accent", className)}>
      {copied ? <Check size={15} /> : <Copy size={15} />}
      {copied ? "Copied!" : label}
    </button>
  );
}
