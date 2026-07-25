import { useRef, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { api } from "@/lib/api";
import { colors, spacing } from "@/lib/theme";

const LONG_PRESS_MS = 1200;

export function SafeRollbackButton({
  buildingId,
  disabled,
  onSuccess,
}: {
  buildingId?: string | null;
  disabled?: boolean;
  onSuccess?: () => void;
}) {
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [holding, setHolding] = useState(false);
  const holdTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const controlsDisabled = disabled || busy || !buildingId;

  const clearHold = () => {
    if (holdTimer.current) {
      clearTimeout(holdTimer.current);
      holdTimer.current = null;
    }
    setHolding(false);
  };

  const openConfirm = () => {
    clearHold();
    setConfirmOpen(true);
    setError(null);
  };

  const runRollback = async () => {
    if (!buildingId) return;
    if (!reason.trim()) {
      setError("Reason is required for emergency rollback");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await api.rollback(buildingId, reason.trim());
      setConfirmOpen(false);
      setReason("");
      Alert.alert("Rollback issued", "Safe policy rollback request was submitted.");
      onSuccess?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Rollback failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <View style={styles.wrap}>
      <Pressable
        disabled={controlsDisabled}
        onPress={() => {
          if (!controlsDisabled) openConfirm();
        }}
        onLongPress={openConfirm}
        delayLongPress={LONG_PRESS_MS}
        onPressIn={() => {
          if (controlsDisabled) return;
          setHolding(true);
          holdTimer.current = setTimeout(() => setHolding(false), LONG_PRESS_MS);
        }}
        onPressOut={clearHold}
        style={[styles.button, controlsDisabled && styles.disabled, holding && styles.holding]}
      >
        <Text style={styles.buttonText}>
          {holding ? "Hold to confirm…" : "Emergency rollback"}
        </Text>
        <Text style={styles.hint}>Long-press or tap for confirmation</Text>
      </Pressable>

      {confirmOpen ? (
        <View style={styles.sheet}>
          <Text style={styles.sheetTitle}>Confirm emergency rollback</Text>
          <Text style={styles.sheetBody}>
            Calls POST /api/v1/buildings/{"{id}"}/rollback with a required reason.
          </Text>
          <TextInput
            style={styles.input}
            placeholder="Reason for rollback…"
            placeholderTextColor={colors.muted}
            value={reason}
            onChangeText={setReason}
            editable={!busy}
            multiline
          />
          {error ? <Text style={styles.error}>{error}</Text> : null}
          <View style={styles.actions}>
            <Pressable
              style={styles.cancel}
              disabled={busy}
              onPress={() => {
                setConfirmOpen(false);
                setReason("");
                setError(null);
              }}
            >
              <Text style={styles.cancelText}>Cancel</Text>
            </Pressable>
            <Pressable
              style={[styles.confirm, busy && styles.disabled]}
              disabled={busy}
              onPress={() => void runRollback()}
            >
              {busy ? (
                <ActivityIndicator color={colors.text} />
              ) : (
                <Text style={styles.confirmText}>Rollback now</Text>
              )}
            </Pressable>
          </View>
        </View>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    gap: spacing.sm,
  },
  button: {
    backgroundColor: "rgba(248,113,113,0.12)",
    borderColor: colors.critical,
    borderWidth: 1,
    borderRadius: 10,
    paddingVertical: spacing.md,
    paddingHorizontal: spacing.lg,
    alignItems: "center",
  },
  holding: {
    backgroundColor: "rgba(248,113,113,0.28)",
  },
  buttonText: {
    color: colors.critical,
    fontWeight: "800",
    fontSize: 14,
    letterSpacing: 0.3,
  },
  hint: {
    marginTop: 4,
    color: colors.muted,
    fontSize: 11,
  },
  sheet: {
    backgroundColor: colors.surfaceMuted,
    borderColor: colors.critical,
    borderWidth: 1,
    borderRadius: 10,
    padding: spacing.md,
  },
  sheetTitle: {
    color: colors.critical,
    fontWeight: "700",
    fontSize: 15,
    marginBottom: 6,
  },
  sheetBody: {
    color: colors.muted,
    fontSize: 12,
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
  actions: {
    flexDirection: "row",
    gap: 8,
    marginTop: spacing.md,
  },
  cancel: {
    flex: 1,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 8,
    paddingVertical: 12,
    alignItems: "center",
  },
  cancelText: {
    color: colors.muted,
    fontWeight: "600",
  },
  confirm: {
    flex: 1,
    backgroundColor: colors.critical,
    borderRadius: 8,
    paddingVertical: 12,
    alignItems: "center",
  },
  confirmText: {
    color: colors.text,
    fontWeight: "800",
  },
  disabled: {
    opacity: 0.45,
  },
});
