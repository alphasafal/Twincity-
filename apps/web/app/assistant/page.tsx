"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { EmptyState, PageHeader, Panel } from "@/components/AppShell";
import { AssistantMessage } from "@/components/AssistantMessage";
import { api } from "@/lib/api";
import { useBuildingId } from "@/lib/hooks";
import type { AssistantAnswer } from "@/lib/types";

type ChatItem =
  | { id: string; role: "user"; content: string }
  | { id: string; role: "assistant"; answer: AssistantAnswer };

export default function AssistantPage() {
  const buildingId = useBuildingId();
  const [message, setMessage] = useState("Why is the current plan recommended?");
  const [conversationId, setConversationId] = useState<string | undefined>();
  const [items, setItems] = useState<ChatItem[]>([]);

  const conversations = useQuery({
    queryKey: ["assistant-conversations"],
    queryFn: () => api.listConversations(),
  });

  const chat = useMutation({
    mutationFn: () => api.assistantChat(buildingId!, message, conversationId),
    onSuccess: (res) => {
      setConversationId(res.conversation_id);
      setItems((prev) => [
        ...prev,
        { id: `${Date.now()}-u`, role: "user", content: message },
        { id: `${Date.now()}-a`, role: "assistant", answer: res.answer },
      ]);
      setMessage("");
    },
  });

  return (
    <div>
      <PageHeader
        title="Assistant"
        description="Evidence-grounded Q&A via /api/v1/assistant/chat. Purple is reserved for AI surfaces."
      />

      <div className="grid gap-4 xl:grid-cols-[240px_1fr]">
        <Panel className="p-3">
          <h2 className="mb-2 px-1 text-xs uppercase tracking-wider text-muted">
            Conversations
          </h2>
          <button
            type="button"
            onClick={() => {
              setConversationId(undefined);
              setItems([]);
            }}
            className="mb-2 w-full rounded border border-border px-2 py-1.5 text-left text-xs text-muted hover:text-foreground"
          >
            New conversation
          </button>
          <div className="space-y-1">
            {(conversations.data || []).map((c) => (
              <button
                key={c.id}
                type="button"
                onClick={async () => {
                  setConversationId(c.id);
                  const full = await api.getConversation(c.id);
                  const mapped: ChatItem[] = [];
                  for (const m of full.messages || []) {
                    const row = m as { role?: string; content?: unknown };
                    if (row.role === "user" && typeof row.content === "string") {
                      mapped.push({
                        id: `${c.id}-${mapped.length}`,
                        role: "user",
                        content: row.content,
                      });
                    } else if (row.role === "assistant") {
                      mapped.push({
                        id: `${c.id}-${mapped.length}`,
                        role: "assistant",
                        answer: (row.content || {}) as AssistantAnswer,
                      });
                    }
                  }
                  setItems(mapped);
                }}
                className="w-full truncate rounded px-2 py-1.5 text-left text-xs text-muted hover:bg-surface-elevated hover:text-foreground"
              >
                {c.title}
              </button>
            ))}
          </div>
        </Panel>

        <Panel className="flex min-h-[520px] flex-col p-4">
          <div className="mb-4 flex-1 space-y-3 overflow-y-auto">
            {!items.length ? (
              <EmptyState>
                Ask about mode, alerts, plans, or a specific decision. Answers cite live API
                context; they are not autonomous control commands.
              </EmptyState>
            ) : (
              items.map((item) =>
                item.role === "user" ? (
                  <AssistantMessage key={item.id} role="user" content={item.content} />
                ) : (
                  <AssistantMessage key={item.id} role="assistant" answer={item.answer} />
                ),
              )
            )}
          </div>
          <form
            className="flex gap-2 border-t border-border pt-3"
            onSubmit={(e) => {
              e.preventDefault();
              if (!buildingId || !message.trim()) return;
              chat.mutate();
            }}
          >
            <input
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              placeholder="Ask TwinPilot…"
              className="flex-1 rounded-md border border-border bg-background px-3 py-2 text-sm outline-none ring-ai/30 focus:ring-2"
            />
            <button
              type="submit"
              disabled={!buildingId || chat.isPending || !message.trim()}
              className="rounded-md bg-ai px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
            >
              {chat.isPending ? "Thinking…" : "Send"}
            </button>
          </form>
          {chat.error ? (
            <p className="mt-2 text-xs text-critical">
              {chat.error instanceof Error ? chat.error.message : "Chat failed"}
            </p>
          ) : null}
        </Panel>
      </div>
    </div>
  );
}
