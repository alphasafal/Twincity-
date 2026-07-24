import { StyleSheet, Text, View } from "react-native";
import { colors, spacing } from "@/lib/theme";

type Tone = "live" | "savings" | "warning" | "critical" | "neutral";

const TONE: Record<Tone, string> = {
  live: colors.live,
  savings: colors.savings,
  warning: colors.warning,
  critical: colors.critical,
  neutral: colors.text,
};

export function MobileKpiCard({
  label,
  value,
  unit,
  hint,
  tone = "neutral",
  simulated,
}: {
  label: string;
  value: string;
  unit?: string;
  hint?: string;
  tone?: Tone;
  simulated?: boolean;
}) {
  return (
    <View style={styles.card}>
      <Text style={styles.label}>{label}</Text>
      <View style={styles.valueRow}>
        <Text style={[styles.value, { color: TONE[tone] }]}>{value}</Text>
        {unit ? <Text style={styles.unit}>{unit}</Text> : null}
      </View>
      {hint ? <Text style={styles.hint}>{hint}</Text> : null}
      {simulated ? <Text style={styles.sim}>Simulated</Text> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    flex: 1,
    minWidth: "45%",
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderWidth: 1,
    borderRadius: 10,
    padding: spacing.md,
  },
  label: {
    color: colors.muted,
    fontSize: 11,
    letterSpacing: 0.8,
    textTransform: "uppercase",
    marginBottom: spacing.sm,
  },
  valueRow: {
    flexDirection: "row",
    alignItems: "baseline",
    gap: 6,
  },
  value: {
    fontSize: 22,
    fontWeight: "700",
    fontVariant: ["tabular-nums"],
  },
  unit: {
    color: colors.muted,
    fontSize: 13,
  },
  hint: {
    marginTop: spacing.sm,
    color: colors.muted,
    fontSize: 11,
  },
  sim: {
    marginTop: spacing.xs,
    alignSelf: "flex-start",
    color: colors.warning,
    fontSize: 10,
    textTransform: "uppercase",
    letterSpacing: 0.6,
  },
});
