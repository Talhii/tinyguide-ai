"use client";

import { useEffect, useRef, useState } from "react";

import { PageHeader } from "@/components/page-header";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { ApiError, api, type AssistantLang } from "@/lib/api";
import { useConversations, type ChatTurn } from "@/lib/chat";

const SUGGESTIONS = [
  "When should my baby start crawling?",
  "How much sleep does a 6-month-old need?",
  "When can I introduce solid food?",
];

const LANGS: { id: AssistantLang; label: string }[] = [
  { id: "en", label: "English" },
  { id: "ur", label: "اردو" },
  { id: "roman", label: "Roman Urdu" },
];

const LANG_KEY = "tinyguide.lang";

function relativeTime(ts: number): string {
  const mins = Math.floor((Date.now() - ts) / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

export default function AssistantPage() {
  const {
    conversations,
    activeId,
    activeMessages,
    setActiveMessages,
    newChat,
    selectChat,
    deleteChat,
  } = useConversations();

  const messages = activeMessages;
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showList, setShowList] = useState(false);
  const [lang, setLang] = useState<AssistantLang>("roman");
  const bottomRef = useRef<HTMLDivElement>(null);

  // Load the saved language preference once.
  useEffect(() => {
    try {
      const s = localStorage.getItem(LANG_KEY);
      if (s === "en" || s === "ur" || s === "roman") setLang(s);
    } catch {
      /* storage unavailable */
    }
  }, []);

  function changeLang(l: AssistantLang) {
    setLang(l);
    try {
      localStorage.setItem(LANG_KEY, l);
    } catch {
      /* storage unavailable */
    }
  }

  useEffect(() => {
    if (!showList) bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading, showList]);

  async function send(text: string) {
    const trimmed = text.trim();
    if (!trimmed || loading) return;

    setError(null);
    const history = messages.map((m) => ({ role: m.role, content: m.content }));
    const userTurn: ChatTurn = { role: "user", content: trimmed };
    const withUser = [...messages, userTurn];
    setActiveMessages(withUser);
    setInput("");
    setLoading(true);

    try {
      const res = await api.askAssistant(trimmed, history, lang);
      const assistantTurn: ChatTurn = {
        role: "assistant",
        content: res.answer,
        isEmergency: res.is_emergency,
        recommendedActions: res.recommended_actions,
        citations: res.citations,
        model: res.model,
      };
      setActiveMessages([...withUser, assistantTurn]);
    } catch (e: unknown) {
      setError(
        e instanceof ApiError
          ? `${e.status}: ${e.message}`
          : e instanceof Error
            ? e.message
            : "Unknown error"
      );
    } finally {
      setLoading(false);
    }
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    void send(input);
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void send(input);
    }
  }

  return (
    <main className="flex min-h-[80dvh] flex-col">
      <PageHeader
        emoji="💬"
        title="AI Assistant"
        subtitle="Saved chats — continue any time."
      />

      {/* Controls */}
      <div className="mb-3 flex gap-2">
        <Button
          variant={showList ? "default" : "outline"}
          size="sm"
          onClick={() => setShowList((v) => !v)}
        >
          🗂️ Chats ({conversations.length})
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={() => {
            newChat();
            setShowList(false);
          }}
        >
          ＋ New
        </Button>
      </div>

      {/* Language selector */}
      <div className="mb-3 flex items-center gap-1.5">
        <span className="text-xs" aria-hidden>
          🌐
        </span>
        {LANGS.map((l) => (
          <button
            key={l.id}
            type="button"
            onClick={() => changeLang(l.id)}
            aria-pressed={lang === l.id}
            className={`rounded-full px-3 py-1 text-xs font-semibold transition-colors ${
              lang === l.id
                ? "bg-primary text-primary-foreground shadow-soft"
                : "border border-border/60 bg-card/70 text-muted-foreground hover:bg-muted"
            }`}
          >
            {l.label}
          </button>
        ))}
      </div>

      {showList ? (
        /* ---------- Saved chats list ---------- */
        <div className="flex-1 space-y-2">
          {conversations.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No saved chats yet. Tap ＋ New and start talking!
            </p>
          ) : (
            conversations.map((c) => (
              <div
                key={c.id}
                className={`flex items-center gap-2 rounded-2xl border p-3 ${
                  c.id === activeId
                    ? "border-primary/60 bg-pastel-peach/40"
                    : "border-border/60 bg-card/70"
                }`}
              >
                <button
                  type="button"
                  onClick={() => {
                    selectChat(c.id);
                    setShowList(false);
                  }}
                  className="min-w-0 flex-1 text-left"
                >
                  <p className="truncate text-sm font-semibold">{c.title}</p>
                  <p className="text-xs text-muted-foreground">
                    {relativeTime(c.updatedAt)} · {c.messages.length} messages
                  </p>
                </button>
                <button
                  type="button"
                  aria-label="Delete chat"
                  onClick={() => deleteChat(c.id)}
                  className="shrink-0 rounded-full p-2 text-muted-foreground transition-colors hover:bg-muted hover:text-primary"
                >
                  🗑️
                </button>
              </div>
            ))
          )}
        </div>
      ) : (
        /* ---------- Active conversation ---------- */
        <>
          <div className="flex-1 space-y-3">
            {messages.length === 0 ? (
              <div className="space-y-2">
                <p className="text-sm text-muted-foreground">Try asking:</p>
                {SUGGESTIONS.map((s) => (
                  <button
                    key={s}
                    type="button"
                    onClick={() => void send(s)}
                    className="block w-full rounded-2xl border border-border/60 bg-card/70 p-3 text-left text-sm hover:bg-muted"
                  >
                    {s}
                  </button>
                ))}
              </div>
            ) : (
              messages.map((m, i) =>
                m.role === "user" ? (
                  <div key={i} className="flex justify-end">
                    <div className="max-w-[85%] rounded-3xl rounded-br-md bg-primary px-4 py-2.5 text-sm text-primary-foreground shadow-soft">
                      {m.content}
                    </div>
                  </div>
                ) : (
                  <div key={i} className="space-y-2">
                    {m.isEmergency ? (
                      <Alert variant="emergency">
                        <AlertTitle>🚨 Possible medical emergency</AlertTitle>
                        <AlertDescription>
                          <ul className="list-disc space-y-1 pl-5 font-semibold">
                            {m.recommendedActions.map((a) => (
                              <li key={a}>{a}</li>
                            ))}
                          </ul>
                        </AlertDescription>
                      </Alert>
                    ) : null}
                    <div className="max-w-[85%] rounded-3xl rounded-bl-md bg-pastel-lavender px-4 py-2.5 text-sm text-foreground shadow-soft">
                      <p className="whitespace-pre-wrap leading-relaxed">
                        {m.content}
                      </p>
                      {m.citations.length > 0 ? (
                        <div className="mt-2 flex flex-wrap items-center gap-1.5">
                          <span className="text-[0.65rem] font-semibold text-muted-foreground">
                            📚
                          </span>
                          {m.citations.map((c) => (
                            <span
                              key={c}
                              className="rounded-full bg-card/70 px-2 py-0.5 text-[0.65rem] font-medium"
                            >
                              {c}
                            </span>
                          ))}
                        </div>
                      ) : null}
                    </div>
                  </div>
                )
              )
            )}

            {loading ? (
              <div className="flex justify-start">
                <div className="rounded-3xl rounded-bl-md bg-pastel-lavender px-4 py-2.5 text-sm text-muted-foreground shadow-soft">
                  Thinking…
                </div>
              </div>
            ) : null}

            {error ? (
              <p className="text-xs text-primary">
                Something went wrong: {error}
              </p>
            ) : null}

            <div ref={bottomRef} />
          </div>

          {/* Composer */}
          <form
            onSubmit={handleSubmit}
            className="sticky bottom-24 mt-4 flex items-end gap-2"
          >
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Type your message…"
              rows={1}
              className="min-h-11 flex-1 resize-none rounded-3xl border border-border bg-card/90 px-4 py-3 text-sm shadow-soft outline-none backdrop-blur focus-visible:ring-2 focus-visible:ring-ring"
            />
            <Button
              type="submit"
              size="icon"
              disabled={loading || !input.trim()}
            >
              <span aria-hidden>↑</span>
              <span className="sr-only">Send</span>
            </Button>
          </form>
        </>
      )}
    </main>
  );
}
