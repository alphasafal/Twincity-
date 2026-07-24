import { router } from "expo-router";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { CompactTelemetryChart } from "@/components/CompactTelemetryChart";
import { ConfidenceRing } from "@/components/ConfidenceRing";
import { MobileKpiCard } from "@/components/MobileKpiCard";
import { ModeBanner } from "@/components/ModeBanner";
import { SafeRollbackButton } from "@/components/SafeRollbackButton";
import { Screen } from "@/components/Screen";
import { useAuthStore } from "@/lib/auth-store";
import {
  useBuildingId,
  useBuildingStatus,
  useInvalidateBuilding,
} from "@/lib/hooks";
import { useOfflineStore } from "@/lib/offline-store";
import { colors, spacing } from "@/lib/theme";
import { formatNumber, formatPct } from "@/lib/utils";

export default function OverviewScreen() {
  const buildingId = useBuildingId();
  const building = useAuthStore((s) => s.building);
  const isOnline = useOfflineStore((s) => s.isOnline);
  const invalidate = useInvalidateBuilding();
  const { data, isLoading, error, refetch, isFetching } = useBuildingStatus(buildingId);

  const chartPoints = (data?.kpi_history || [])
    .slice(-24)
    .map((p, idx) => ({
      value: Number(p.power_kw ?? 0),
      label: idx % 6 === 0 ? String(idx) : undefined,
    }));

  return (
    <Screen
      title="Overview"
      subtitle={building?.name || "Building status"}
      loading={isLoading && !data}
      error={error instanceof Error ? error.message : null}
      right={
        <Pressable
          onPress={() => void refetch()}
          disabled={!isOnline || isFetching}
          style={styles.refresh}
        >
          <Text style={[styles.refreshText, (!isOnline || isFetching) && styles.dim]}>
            Refresh
          </Text>
        </Pressable>
      }
    >
      {data?.simulated || building?.is_demo ? (
        <View style={styles.simBanner}>
          <Text style={styles.simText}>Simulated data</Text>
        </View>
      ) : null}

      <ModeBanner mode={data?.mode || building?.current_mode} />

      <View style={styles.hero}>
        <ConfidenceRing confidence={data?.confidence ?? building?.confidence} />
        <View style={styles.heroMeta}>
          <Text style={styles.modeLabel}>Operating mode</Text>
          <Text style={styles.modeValue}>
            {(data?.mode || building?.current_mode || "—").toString()}
          </Text>
          <Text style={styles.scenario}>
            Scenario: {data?.active_scenario || "normal"}
          </Text>
          <Pressable onPress={() => router.push("/assistant")} style={styles.linkBtn}>
            <Text style={styles.linkText}>Ask assistant</Text>
          </Pressable>
        </View>
      </View>

      <View style={styles.kpiGrid}>
        <MobileKpiCard
          label="Live load"
          value={formatNumber(data?.live_total_load_kw)}
          unit="kW"
          tone="live"
          hint={building?.location}
          simulated={data?.simulated}
        />
        <MobileKpiCard
          label="Energy saved"
          value={formatPct(data?.energy_saved_today_pct)}
          tone="savings"
          simulated={data?.simulated}
        />
        <MobileKpiCard
          label="Cost saved"
          value={formatNumber(data?.cost_saved_today)}
          unit="$"
          tone="savings"
          simulated={data?.simulated}
        />
        <MobileKpiCard
          label="Carbon avoided"
          value={formatNumber(data?.carbon_avoided_today_kg)}
          unit="kg"
          tone="savings"
          simulated={data?.simulated}
        />
        <MobileKpiCard
          label="Comfort"
          value={formatPct(data?.comfort_compliance_pct)}
          tone="live"
        />
        <MobileKpiCard
          label="Active alerts"
          value={String(data?.active_alerts ?? 0)}
          tone={(data?.active_alerts ?? 0) > 0 ? "warning" : "neutral"}
          hint={`${data?.pending_decisions ?? 0} pending decisions`}
        />
      </View>

      <View style={styles.section}>
        <CompactTelemetryChart title="Building power (recent)" points={chartPoints} />
      </View>

      <View style={styles.section}>
        <SafeRollbackButton
          buildingId={buildingId}
          disabled={!isOnline}
          onSuccess={() => invalidate(buildingId)}
        />
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  refresh: {
    paddingVertical: 6,
    paddingHorizontal: 10,
  },
  refreshText: {
    color: colors.live,
    fontWeight: "700",
    fontSize: 13,
  },
  dim: {
    opacity: 0.45,
  },
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
    letterSpacing: 0.6,
    textTransform: "uppercase",
  },
  hero: {
    flexDirection: "row",
    gap: spacing.lg,
    alignItems: "center",
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderWidth: 1,
    borderRadius: 12,
    padding: spacing.lg,
    marginBottom: spacing.md,
  },
  heroMeta: {
    flex: 1,
  },
  modeLabel: {
    color: colors.muted,
    fontSize: 11,
    letterSpacing: 0.8,
    textTransform: "uppercase",
  },
  modeValue: {
    color: colors.text,
    fontSize: 18,
    fontWeight: "700",
    marginTop: 4,
  },
  scenario: {
    color: colors.muted,
    fontSize: 12,
    marginTop: 6,
  },
  linkBtn: {
    marginTop: spacing.md,
    alignSelf: "flex-start",
  },
  linkText: {
    color: colors.live,
    fontWeight: "700",
    fontSize: 13,
  },
  kpiGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.sm,
  },
  section: {
    marginTop: spacing.lg,
  },
});
