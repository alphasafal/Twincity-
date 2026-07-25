import { Pressable, StyleSheet, Text, View } from "react-native";
import type { Alert } from "@/lib/types";
import { colors, spacing } from "@/lib/theme";
import { formatTs, severityColor } from "@/lib/utils";

export function AlertListItem({
  alert,
  onPress,
}: {
  alert: Alert;
  onPress?: () => void;
}) {
  const color = severityColor(alert.severity);

  return (
    <Pressable
      onPress={onPress}
      style={({ pressed }) => [styles.item, pressed && styles.pressed]}
      disabled={!onPress}
    >
      <View style={[styles.dot, { backgroundColor: color }]} />
      <View style={styles.body}>
        <View style={styles.top}>
          <Text style={styles.title} numberOfLines={1}>
            {alert.title}
          </Text>
          <Text style={[styles.severity, { color }]}>{alert.severity}</Text>
        </View>
        <Text style={styles.message} numberOfLines={2}>
          {alert.message}
        </Text>
        <Text style={styles.meta}>
          {alert.status} · {formatTs(alert.created_at)}
        </Text>
      </View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  item: {
    flexDirection: "row",
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderWidth: 1,
    borderRadius: 10,
    padding: spacing.md,
    marginBottom: spacing.sm,
    gap: spacing.md,
  },
  pressed: {
    opacity: 0.85,
  },
  dot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    marginTop: 6,
  },
  body: {
    flex: 1,
  },
  top: {
    flexDirection: "row",
    justifyContent: "space-between",
    gap: spacing.sm,
    marginBottom: 4,
  },
  title: {
    color: colors.text,
    fontWeight: "600",
    fontSize: 14,
    flex: 1,
  },
  severity: {
    fontSize: 11,
    fontWeight: "700",
    letterSpacing: 0.5,
    textTransform: "uppercase",
  },
  message: {
    color: colors.muted,
    fontSize: 13,
    lineHeight: 18,
  },
  meta: {
    marginTop: 6,
    color: colors.muted,
    fontSize: 11,
  },
});
