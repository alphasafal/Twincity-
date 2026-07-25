import { StyleSheet, Text, View } from "react-native";
import { LineChart } from "react-native-gifted-charts";
import { colors, spacing } from "@/lib/theme";

export function CompactTelemetryChart({
  title = "Power",
  points,
  height = 140,
}: {
  title?: string;
  points: Array<{ value: number; label?: string }>;
  height?: number;
}) {
  if (!points.length) {
    return (
      <View style={styles.card}>
        <Text style={styles.title}>{title}</Text>
        <Text style={styles.empty}>No telemetry points</Text>
      </View>
    );
  }

  const data = points.map((p) => ({
    value: p.value,
    label: p.label,
  }));

  return (
    <View style={styles.card}>
      <Text style={styles.title}>{title}</Text>
      <LineChart
        data={data}
        height={height}
        width={280}
        spacing={Math.max(8, Math.floor(260 / Math.max(points.length, 1)))}
        color={colors.live}
        thickness={2}
        startFillColor="rgba(34,211,238,0.35)"
        endFillColor="rgba(34,211,238,0.02)"
        startOpacity={0.4}
        endOpacity={0.05}
        areaChart
        hideDataPoints
        hideRules
        yAxisColor={colors.border}
        xAxisColor={colors.border}
        yAxisTextStyle={styles.axis}
        xAxisLabelTextStyle={styles.axis}
        noOfSections={4}
        backgroundColor={colors.surface}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderWidth: 1,
    borderRadius: 10,
    padding: spacing.md,
    overflow: "hidden",
  },
  title: {
    color: colors.text,
    fontSize: 13,
    fontWeight: "600",
    marginBottom: spacing.sm,
  },
  empty: {
    color: colors.muted,
    fontSize: 13,
    paddingVertical: spacing.xl,
  },
  axis: {
    color: colors.muted,
    fontSize: 10,
  },
});
