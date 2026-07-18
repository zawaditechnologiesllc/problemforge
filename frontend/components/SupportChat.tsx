"use client";

import { Loader2, MessageCircle, Send, X } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { getSupportThread, sendSupportMessage } from "@/lib/api";
import { getSupabase } from "@/lib/supabase/client";
import type { SupportMessage } from "@/lib/types";
import clsx from "clsx";

export function SupportChat() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const [signedIn, setSignedIn] = useState(false);
  const [messages, setMessages] = useState<SupportMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [sending, setSending] = useState(false);
  const [unread, setUnread] = useState(0);
  const bottomRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const supabase = getSupabase();
    supabase.auth
      .getSession()
      .then(({ data }) => setSignedIn(!!data.session))
      .catch(() => setSignedIn(false));
    const { data: sub } = supabase.auth.onAuthStateChange((_e, session) =>
      setSignedIn(!!session)
    );
    return () => sub.subscription.unsubscribe();
  }, []);

  const refresh = useCallback(
    (markRead: boolean) => {
      if (!signedIn) return;
      getSupportThread(markRead)
        .then((data) => {
          setMessages(data.messages);
          setUnread(markRead ? 0 : data.unread);
        })
        .catch(() => undefined);
    },
    [signedIn]
  );

  // Light unread poll while closed; faster message poll while open.
  useEffect(() => {
    if (!signedIn) return;
    refresh(open);
    const timer = setInterval(() => refresh(open), open ? 8000 : 60000);
    return () => clearInterval(timer);
  }, [signedIn, open, refresh]);

  useEffect(() => {
    if (open) bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length, open]);

  async function send(event: React.FormEvent) {
    event.preventDefault();
    const body = draft.trim();
    if (!body || sending) return;
    setSending(true);
    try {
      const { message } = await sendSupportMessage(body);
      setMessages((current) => [...current, message]);
      setDraft("");
    } catch {
      // keep the draft so nothing is lost
    } finally {
      setSending(false);
    }
  }

  // Keep the admin panel clean — it has its own Messages tab.
  if (pathname.startsWith("/admin")) return null;

  return (
    <>
      {/* Floating bubble */}
      <button
        onClick={() => setOpen((v) => !v)}
        aria-label={open ? "Close support chat" : "Open support chat"}
        className="fixed bottom-5 right-5 z-50 flex h-[52px] w-[52px] items-center justify-center rounded-full bg-accent text-base shadow-lg transition hover:bg-accent-hover"
      >
        {open ? <X size={22} /> : <MessageCircle size={22} />}
        {!open && unread > 0 && (
          <span className="absolute -right-0.5 -top-0.5 flex h-5 min-w-5 items-center justify-center rounded-full bg-red-400 px-1 text-[11px] font-bold text-base">
            {unread}
          </span>
        )}
      </button>

      {/* Panel */}
      {open && (
        <div className="fixed bottom-20 right-4 z-50 flex max-h-[70vh] w-[calc(100vw-2rem)] max-w-sm flex-col overflow-hidden rounded-card border border-edge bg-surface shadow-2xl sm:right-5">
          <div className="border-b border-edge px-4 py-3">
            <p className="text-sm font-semibold">Support</p>
            <p className="text-xs text-muted">
              We reply here and by email — usually within a day.
            </p>
          </div>

          {!signedIn ? (
            <div className="p-6 text-center">
              <p className="text-sm text-muted">
                Sign in to chat with support so we can keep the conversation
                attached to your account.
              </p>
              <Link href="/login" className="btn-accent mt-4 w-full">
                Sign In
              </Link>
            </div>
          ) : (
            <>
              <div className="flex-1 space-y-3 overflow-y-auto p-4">
                {messages.length === 0 && (
                  <p className="py-6 text-center text-sm text-muted">
                    How can we help? Billing, blueprints, API — ask away.
                  </p>
                )}
                {messages.map((message) => (
                  <div
                    key={message.id}
                    className={clsx(
                      "max-w-[85%] rounded-xl px-3.5 py-2.5 text-sm leading-relaxed",
                      message.sender === "user"
                        ? "ml-auto bg-accent-soft text-ink"
                        : "bg-raised text-ink/90"
                    )}
                  >
                    {message.body}
                    <p className="mt-1 text-[10px] text-muted">
                      {message.sender === "admin" ? "Support · " : ""}
                      {new Date(message.created_at).toLocaleTimeString([], {
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </p>
                  </div>
                ))}
                <div ref={bottomRef} />
              </div>
              <form onSubmit={send} className="flex gap-2 border-t border-edge p-3">
                <input
                  className="input flex-1 py-2"
                  placeholder="Type a message..."
                  value={draft}
                  maxLength={2000}
                  onChange={(event) => setDraft(event.target.value)}
                />
                <button
                  type="submit"
                  disabled={sending || !draft.trim()}
                  className="btn-accent px-3 py-2"
                  aria-label="Send message"
                >
                  {sending ? (
                    <Loader2 className="animate-spin" size={16} />
                  ) : (
                    <Send size={16} />
                  )}
                </button>
              </form>
            </>
          )}
        </div>
      )}
    </>
  );
}
