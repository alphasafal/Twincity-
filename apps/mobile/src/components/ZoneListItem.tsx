import { Pressable, StyleSheet, Text, View } from "react-native";
import { colors, spacing } from "@/lib/theme";
import { formatNumber } from "@/lib/utils";

export function ZoneListItem({
  name,
  floor,
  temperature,
  comfortStatus,
  sensorHealth,
  onPress,
}: {
  name: string;
  floor: number;
  temperature?: number | null;
  comfortStatus?: string | null;
  sensorHealth?: number | null;
  onPress?: () => void;
}) {
  const comfort = (comfortStatus || "unknown").replaceAll("_", " ");
  const healthPct =
    sensorHealth == null ? null : Math.round(Math.max(0, Math.min(1, sensorHealth)) * 100);

  return (
    <Pressable
      onPress={onPress}
      style={({ pressed }) => [styles.item, pressed && styles.pressed]}
      disabled={!onPress}
    >
      <View style={styles.top}>
        <Text style={styles.name}>{name}</Text>
        <Text style={styles.temp}>
          {temperature == null ? "—" : `${formatNumber(temperature)}°C`}
        </Text>
      </View>
      <View style={styles.meta}>
        <Text style={styles.metaText}>Floor {floor}</Text>
        <Text style={styles.metaText}>{comfort}</Text>
        <Text style={styles.metaText}>
          Sensors {healthPct == null ? "—" : `${healthPct}%`}
        </Text>
      </View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  item: {
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderWidth: 1,
    borderRadius: 10,
    padding: spacing.md,
    marginBottom: spacing.sm,
  },
  pressed: {
    opacity: 0.85,
  },
  top: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 6,
  },
  name: {
    color: colors.text,
    fontSize: 15,
    fontWeight: "600",
    flex: 1,
    marginRight: spacing.sm,
  },
  temp: {
    color: colors.live,
    fontSize: 16,
    fontWeight: "700",
    fontVariant: ["tabular-nums"],
  },
  meta: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 10,
  },
  metaText: {
    color: colors.muted,
    fontSize: 12,
    textTransform: "capitalize",
  },
});
