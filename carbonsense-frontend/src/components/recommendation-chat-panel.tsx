import { useEffect, useRef, useState } from "react";
import { MessageSquare, Send, Loader2, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { chatRecommendation, fetchChatHistory } from "@/lib/api";
import type { ChatMessage } from "@/lib/api";

interface RecommendationChatPanelProps {
  recommendationId: string;
  areaName: string;
  sector: string;
}

export function RecommendationChatPanel({
  recommendationId,
  areaName,
  sector,
}: RecommendationChatPanelProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement | null>(null);

  // Load existing history once
  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const data = await fetchChatHistory(recommendationId);
        if (active && data?.messages?.length) {
          setMessages(data.messages);
        }
      } catch (err) {
        // No prior history is normal; only log other failures.
        console.debug("No prior chat history", err);
      }
    })();
    return () => {
      active = false;
    };
  }, [recommendationId]);

  // Scroll to bottom on new messages
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, sending]);

  const handleSend = async () => {
    const text = input.trim();
    if (!text || sending) return;

    setSending(true);
    setError(null);
    const optimistic: ChatMessage = {
      role: "user",
      content: text,
      ts: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, optimistic]);
    setInput("");

    try {
      const result = await chatRecommendation(recommendationId, text);
      // Replace local messages with server-authoritative history (which now
      // includes the assistant's reply).
      setMessages(result.history || []);
    } catch (err: any) {
      console.error("Chat failed", err);
      setError(err?.message || "Chat failed. Please try again.");
      // Roll back optimistic user message so they can retry.
      setMessages((prev) => prev.filter((m) => m !== optimistic));
    } finally {
      setSending(false);
    }
  };

  const onKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const suggestions = [
    `What is the single highest-impact action we can take in ${areaName} this year?`,
    `Show me a global case study for ${sector} we can adapt.`,
    `Why is the top recommendation prioritized over the others?`,
  ];

  return (
    <section className="border-t border-border bg-muted/10">
      <div className="px-6 py-4 flex items-center gap-2 border-b border-border">
        <MessageSquare className="h-4 w-4 text-emerald-500" />
        <h3 className="font-semibold text-sm">Ask a follow-up question</h3>
        <span className="text-xs text-muted-foreground ml-auto">
          Grounded in this recommendation
        </span>
      </div>

      <div className="px-6 py-4">
        <ScrollArea className="max-h-72">
          <div ref={scrollRef} className="flex flex-col gap-3 pr-3">
            {messages.length === 0 && !sending && (
              <div className="text-xs text-muted-foreground space-y-2">
                <p>Try asking:</p>
                <ul className="space-y-1">
                  {suggestions.map((s, i) => (
                    <li key={i}>
                      <button
                        type="button"
                        className="text-left text-emerald-600 hover:underline"
                        onClick={() => setInput(s)}
                      >
                        — {s}
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {messages.map((m, i) => (
              <div
                key={`${m.ts}-${i}`}
                className={`max-w-[85%] rounded-lg px-3 py-2 text-sm leading-relaxed ${
                  m.role === "user"
                    ? "self-end bg-emerald-500/10 border border-emerald-500/30"
                    : "self-start bg-card border border-border"
                }`}
              >
                <div className="flex items-center gap-1.5 text-[10px] uppercase tracking-wide text-muted-foreground mb-1">
                  {m.role === "assistant" && <Sparkles className="h-3 w-3" />}
                  <span>{m.role === "user" ? "You" : "Advisor"}</span>
                </div>
                <p className="whitespace-pre-wrap break-words">{m.content}</p>
              </div>
            ))}

            {sending && (
              <div className="self-start flex items-center gap-2 text-xs text-muted-foreground">
                <Loader2 className="h-3 w-3 animate-spin" />
                Drafting reply...
              </div>
            )}
          </div>
        </ScrollArea>

        {error && (
          <p className="text-xs text-red-500 mt-2">{error}</p>
        )}

        <div className="flex gap-2 mt-3">
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={onKeyDown}
            placeholder={`Ask about the recommendation for ${areaName}...`}
            disabled={sending}
          />
          <Button
            type="button"
            onClick={handleSend}
            disabled={sending || !input.trim()}
            className="shrink-0"
          >
            {sending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
          </Button>
        </div>
      </div>
    </section>
  );
}
