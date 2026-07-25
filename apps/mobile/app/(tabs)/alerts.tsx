import { router } from "expo-router";
import { useEffect, useRef } from "react";
import { StyleSheet, Text, View } from "react-native";
import { AlertListItem } from "@/components/AlertListItem";
import { Screen } from "@/components/Screen";
import { useAlerts, useBuildingId } from "@/lib/hooks";
import { notifyCriticalAlert } from "@/lib/notifications";
import { colors, spacing } from "@/lib/theme";

export default function AlertsScreen() {
  const buildingId = useBuildingId();
  const { data, isLoading, error } = useAlerts(buildingId);
  const seenCritical = useRef<Set<string>>(new Set());

  useEffect(() => {
    if (!data?.length) return;
    for (const alert of data) {
      if (alert.severity.toUpperCase() !== "CRITICAL") continue;
      if (alert.status.toUpperCase() === "RESOLVED") continue;
      if (seenCritical.current.has(alert.id)) continue;
      seenCritical.current.add(alert.id);
      void notifyCriticalAlert(alert.title, alert.message);
    }
  }, [data]);

  const open = (data || []).filter((a) => a.status.toUpperCase() !== "RESOLVED");
  const resolved = (data || []).filter((a) => a.status.toUpperCase() === "RESOLVED");

  return (
    <Screen
      title="Alerts"
      subtitle="Operational alerts from the digital twin"
      loading={isLoading && !data}
      error={error instanceof Error ? error.message : null}
    >
      <View style={styles.simBanner}>
        <Text style={styles.simText}>Demo local notifications for critical alerts</Text>
      </View>

      <Text style={styles.section}>Open</Text>
      {open.map((alert) => (
        <AlertListItem
          key={alert.id}
          alert={alert}
          onPress={() => router.push(`/alerts/${alert.id}`)}
        />
      ))}
      {!isLoading && !open.length ? (
        <Text style={styles.empty}>No open alerts.</Text>
      ) : null}

      {resolved.length ? (
        <>
          <Text style={[styles.section, styles.sectionSpaced]}>Resolved</Text>
          {resolved.slice(0, 10).map((alert) => (
            <AlertListItem
              key={alert.id}
              alert={alert}
              onPress={() => router.push(`/alerts/${alert.id}`)}
            />
          ))}
        </>
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
  section: {
    color: colors.muted,
    fontSize: 11,
    letterSpacing: 1,
    textTransform: "uppercase",
    fontWeight: "700",
    marginBottom: spacing.sm,
  },
  sectionSpaced: {
    marginTop: spacing.lg,
  },
  empty: {
    color: colors.muted,
    fontSize: 14,
  },
});
