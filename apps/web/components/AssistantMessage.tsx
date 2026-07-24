"use client";

import type { AssistantAnswer } from "@/lib/types";
import { cn, formatPct } from "@/lib/utils";

export function AssistantMessage({
  role,
  content,
  answer,
}: {
  role: "user" | "assistant";
  content?: string;
  answer?: AssistantAnswer | null;
}) {
  const isUser = role === "user";
  return (
    <div
      className={cn(
        "max-w-3xl rounded-lg border px-4 py-3 text-sm animate-fade-up",
        isUser
          ? "ml-auto border-border bg-surface text-foreground"
          : "mr-auto border-ai/30 bg-ai/5 text-foreground",
      )}
    >
      <div
        className={cn(
          "mb-1 font-mono text-[10px] uppercase tracking-wider",
          isUser ? "text-muted" : "text-ai",
        )}
      >
        {isUser ? "You" : "TwinPilot Assistant"}
      </div>
      {isUser ? (
        <p>{content}</p>
      ) : (
        <div className="space-y-2">
          {answer?.summary ? <p className="font-medium">{String(answer.summary)}</p> : null}
          {answer?.explanation ? (
            <p className="text-muted">{String(answer.explanation)}</p>
          ) : null}
          {!answer?.summary && !answer?.explanation && content ? <p>{content}</p> : null}
          {typeof answer?.confidence === "number" ? (
            <div className="text-xs text-muted">
              Model confidence: {formatPct(answer.confidence * 100, 0)}
            </div>
          ) : null}
          {Array.isArray(answer?.recommended_actions) &&
          answer.recommended_actions.length ? (
            <ul className="list-disc space-y-1 pl-4 text-xs text-muted">
              {answer.recommended_actions.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          ) : null}
        </div>
      )}
    </div>
  );
}
