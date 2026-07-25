import { useQuery } from "@tanstack/react-query";
import { useLocalSearchParams } from "expo-router";
import { StyleSheet, Text, View } from "react-native";
import { CompactTelemetryChart } from "@/components/CompactTelemetryChart";
import { MobileKpiCard } from "@/components/MobileKpiCard";
import { Screen } from "@/components/Screen";
import { api } from "@/lib/api";
import { useOfflineStore } from "@/lib/offline-store";
import { colors, spacing } from "@/lib/theme";
import { formatNumber } from "@/lib/utils";

export default function ZoneDetailScreen() {
  const { zoneId } = useLocalSearchParams<{ zoneId: string }>();
  const isOnline = useOfflineStore((s) => s.isOnline);

  const zoneQuery = useQuery({
    queryKey: ["zone", zoneId],
    queryFn: () => api.getZone(zoneId!),
    enabled: Boolean(zoneId) && isOnline,
  });
  const healthQuery = useQuery({
    queryKey: ["zone-health", zoneId],
    queryFn: () => api.zoneHealth(zoneId!),
    enabled: Boolean(zoneId) && isOnline,
    refetchInterval: isOnline ? 10_000 : false,
  });
  const telemetryQuery = useQuery({
    queryKey: ["zone-telemetry", zoneId],
    queryFn: () => api.zoneTelemetry(zoneId!, 80),
    enabled: Boolean(zoneId) && isOnline,
  });

  const zone = zoneQuery.data;
  const health = healthQuery.data;
  const live = (health?.live || {}) as Record<string, unknown>;
  const temperature =
    typeof live.temperature === "number"
      ? live.temperature
      : health?.estimated_temperature;

  const tempPoints = (telemetryQuery.data || [])
    .filter((p) => p.metric === "temperature" || p.metric.includes("temp"))
    .slice()
    .reverse()
    .slice(-30)
    .map((p, idx) => ({
      value: p.value,
      label: idx % 8 === 0 ? String(idx) : undefined,
    }));

  const loading =
    (zoneQuery.isLoading || healthQuery.isLoading) && !zone && !health;
  const err =
    zoneQuery.error instanceof Error
      ? zoneQuery.error.message
      : healthQuery.error instanceof Error
        ? healthQuery.error.message
        : null;

  return (
    <Screen
      title={zone?.name || "Zone"}
      subtitle={zone ? `Floor ${zone.floor} · ${zone.area_m2} m²` : "Zone detail"}
      loading={loading}
      error={err}
    >
      <View style={styles.simBanner}>
        <Text style={styles.simText}>Simulated telemetry when demo building</Text>
      </View>

      <View style={styles.kpiGrid}>
        <MobileKpiCard
          label="Temperature"
          value={formatNumber(typeof temperature === "number" ? temperature : null)}
          unit="°C"
          tone="live"
          simulated
        />
        <MobileKpiCard
          label="Comfort"
          value={String(health?.comfort_status || live.comfort_status || "—")}
          tone="neutral"
        />
        <MobileKpiCard
          label="Sensor health"
          value={
            health?.sensor_health == null
              ? "—"
              : `${Math.round(health.sensor_health * 100)}%`
          }
          tone={health?.sensor_failed ? "critical" : "savings"}
        />
        <MobileKpiCard
          label="Preferred"
          value={formatNumber(zone?.preferred_temperature)}
          unit="°C"
          hint={`${zone?.minimum_temperature ?? "—"}–${zone?.maximum_temperature ?? "—"} °C band`}
        />
      </View>

      <View style={styles.section}>
        <CompactTelemetryChart title="Temperature history" points={tempPoints} />
      </View>

      {health?.data_freshness_seconds != null ? (
        <Text style={styles.meta}>
          Data freshness: {Math.round(health.data_freshness_seconds)}s
        </Text>
      ) : null}
    </Screen>
  );
}

const styles = StyleSheet.create({
  simBanner: {
    alignSelf: "flex-start",
    backgroundColor: "rgba(251,191,36,0.12)",
    borderColor: colors.warning,
    borderWidth: 1,
    borderRadius: 6,
    paddingHorizontal: 10,
    paddingVertical: 4,
    marginBottom: spacing.md,
  },
  simText: {
    color: colors.warning,
    fontSize: 11,
    fontWeight: "700",
    letterSpacing: 0.4,
    textTransform: "uppercase",
  },
  kpiGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.sm,
  },
  section: {
    marginTop: spacing.lg,
  },
  meta: {
    marginTop: spacing.md,
    color: colors.muted,
    fontSize: 12,
  },
});
