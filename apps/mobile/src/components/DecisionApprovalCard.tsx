import { useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import type { Decision } from "@/lib/types";
import { colors, spacing } from "@/lib/theme";
import { formatPct, formatTs } from "@/lib/utils";

type Action = "approve" | "reject" | "revise";

export function DecisionApprovalCard({
  decision,
  disabled,
  busy,
  onApprove,
  onReject,
  onRequestRevised,
}: {
  decision: Decision;
  disabled?: boolean;
  busy?: boolean;
  onApprove: (reason: string) => Promise<void> | void;
  onReject: (reason: string) => Promise<void> | void;
  onRequestRevised: (reason: string) => Promise<void> | void;
}) {
  const [action, setAction] = useState<Action | null>(null);
  const [reason, setReason] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const needsReason = action === "reject" || action === "revise";
  const controlsDisabled = disabled || busy || submitting;

  const submit = async () => {
    if (!action) return;
    if (needsReason && !reason.trim()) {
      setError("Reason is required");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      if (action === "approve") {
        await onApprove(reason.trim() || "Approved from mobile");
      } else if (action === "reject") {
        await onReject(reason.trim());
      } else {
        await onRequestRevised(reason.trim());
      }
      setAction(null);
      setReason("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Action failed");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <View style={styles.card}>
      <View style={styles.top}>
        <Text style={styles.mode}>{decision.mode}</Text>
        <Text style={styles.status}>{decision.execution_status}</Text>
      </View>
      <Text style={styles.trigger}>{decision.trigger}</Text>
      <Text style={styles.explanation} numberOfLines={3}>
        {decision.explanation || "No explanation stored."}
      </Text>
      <Text style={styles.meta}>
        Confidence {formatPct(decision.confidence * 100, 0)} · {formatTs(decision.created_at)}
      </Text>

      {decision.execution_status === "PENDING" ? (
        <>
          <View style={styles.actions}>
            <ActionBtn
              label="Approve"
              tone="savings"
              disabled={controlsDisabled}
              onPress={() => {
                setAction("approve");
                setError(null);
              }}
            />
            <ActionBtn
              label="Reject"
              tone="critical"
              disabled={controlsDisabled}
              onPress={() => {
                setAction("reject");
                setError(null);
              }}
            />
            <ActionBtn
              label="Revise"
              tone="warning"
              disabled={controlsDisabled}
              onPress={() => {
                setAction("revise");
                setError(null);
              }}
            />
          </View>

          {action ? (
            <View style={styles.confirm}>
              <Text style={styles.confirmTitle}>
                {action === "approve"
                  ? "Confirm approval"
                  : action === "reject"
                    ? "Reject plan"
                    : "Request revised plan"}
              </Text>
              {needsReason || action === "approve" ? (
                <TextInput
                  style={styles.input}
                  placeholder={
                    needsReason ? "Reason required…" : "Optional note…"
                  }
                  placeholderTextColor={colors.muted}
                  value={reason}
                  onChangeText={setReason}
                  editable={!controlsDisabled}
                  multiline
                />
              ) : null}
              {error ? <Text style={styles.error}>{error}</Text> : null}
              <View style={styles.confirmActions}>
                <Pressable
                  style={[styles.secondaryBtn, controlsDisabled && styles.disabled]}
                  disabled={controlsDisabled}
                  onPress={() => {
                    setAction(null);
                    setReason("");
                    setError(null);
                  }}
                >
                  <Text style={styles.secondaryText}>Cancel</Text>
                </Pressable>
                <Pressable
                  style={[styles.primaryBtn, controlsDisabled && styles.disabled]}
                  disabled={controlsDisabled}
                  onPress={() => void submit()}
                >
                  {submitting ? (
                    <ActivityIndicator color={colors.bg} />
                  ) : (
                    <Text style={styles.primaryText}>Confirm</Text>
                  )}
                </Pressable>
              </View>
            </View>
          ) : null}
        </>
      ) : null}
    </View>
  );
}

function ActionBtn({
  label,
  tone,
  disabled,
  onPress,
}: {
  label: string;
  tone: "savings" | "critical" | "warning";
  disabled?: boolean;
  onPress: () => void;
}) {
  const color =
    tone === "savings"
      ? colors.savings
      : tone === "critical"
        ? colors.critical
        : colors.warning;
  return (
    <Pressable
      onPress={onPress}
      disabled={disabled}
      style={[styles.actionBtn, { borderColor: color }, disabled && styles.disabled]}
    >
      <Text style={[styles.actionText, { color }]}>{label}</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderWidth: 1,
    borderRadius: 10,
    padding: spacing.md,
    marginBottom: spacing.sm,
  },
  top: {
    flexDirection: "row",
    justifyContent: "space-between",
    marginBottom: 6,
  },
  mode: {
    color: colors.live,
    fontSize: 11,
    fontWeight: "700",
    letterSpacing: 0.6,
    textTransform: "uppercase",
  },
  status: {
    color: colors.muted,
    fontSize: 11,
    textTransform: "uppercase",
  },
  trigger: {
    color: colors.text,
    fontWeight: "600",
    fontSize: 15,
    marginBottom: 4,
  },
  explanation: {
    color: colors.muted,
    fontSize: 13,
    lineHeight: 18,
  },
  meta: {
    marginTop: 8,
    color: colors.muted,
    fontSize: 11,
  },
  actions: {
    flexDirection: "row",
    gap: 8,
    marginTop: spacing.md,
  },
  actionBtn: {
    flex: 1,
    borderWidth: 1,
    borderRadius: 8,
    paddingVertical: 10,
    alignItems: "center",
  },
  actionText: {
    fontSize: 12,
    fontWeight: "700",
  },
  confirm: {
    marginTop: spacing.md,
    borderTopWidth: 1,
    borderTopColor: colors.border,
    paddingTop: spacing.md,
  },
  confirmTitle: {
    color: colors.text,
    fontWeight: "600",
    marginBottom: spacing.sm,
  },
  input: {
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.bg,
    borderRadius: 8,
    color: colors.text,
    padding: spacing.md,
    minHeight: 72,
    textAlignVertical: "top",
  },
  error: {
    color: colors.critical,
    marginTop: spacing.sm,
    fontSize: 12,
  },
  confirmActions: {
    flexDirection: "row",
    gap: 8,
    marginTop: spacing.md,
  },
  secondaryBtn: {
    flex: 1,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 8,
    paddingVertical: 12,
    alignItems: "center",
  },
  secondaryText: {
    color: colors.muted,
    fontWeight: "600",
  },
  primaryBtn: {
    flex: 1,
    backgroundColor: colors.live,
    borderRadius: 8,
    paddingVertical: 12,
    alignItems: "center",
  },
  primaryText: {
    color: colors.bg,
    fontWeight: "700",
  },
  disabled: {
    opacity: 0.45,
  },
});
