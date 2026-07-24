import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useLocalSearchParams } from "expo-router";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { Screen } from "@/components/Screen";
import { api } from "@/lib/api";
import { useBuildingId } from "@/lib/hooks";
import { useOfflineStore } from "@/lib/offline-store";
import { colors, spacing } from "@/lib/theme";
import { formatTs, severityColor } from "@/lib/utils";

export default function AlertDetailScreen() {
  const { alertId } = useLocalSearchParams<{ alertId: string }>();
  const buildingId = useBuildingId();
  const isOnline = useOfflineStore((s) => s.isOnline);
  const queryClient = useQueryClient();

  const alertsQuery = useQuery({
    queryKey: ["alerts", buildingId],
    queryFn: () => api.listAlerts(buildingId!),
    enabled: Boolean(buildingId) && isOnline,
  });

  const alert = (alertsQuery.data || []).find((a) => a.id === alertId);

  const ackMut = useMutation({
    mutationFn: () => api.ackAlert(alertId!),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["alerts", buildingId] });
    },
  });
  const resolveMut = useMutation({
    mutationFn: () => api.resolveAlert(alertId!),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["alerts", buildingId] });
    },
  });

  const busy = ackMut.isPending || resolveMut.isPending;
  const controlsDisabled = !isOnline || busy || !alert;

  return (
    <Screen
      title="Alert"
      subtitle={alert?.alert_type || "Alert detail"}
      loading={alertsQuery.isLoading && !alert}
      error={
        alertsQuery.error instanceof Error
          ? alertsQuery.error.message
          : !alertsQuery.isLoading && !alert
            ? "Alert not found in current building feed"
            : null
      }
    >
      {alert ? (
        <>
          <View style={styles.card}>
            <Text style={[styles.severity, { color: severityColor(alert.severity) }]}>
              {alert.severity}
            </Text>
            <Text style={styles.title}>{alert.title}</Text>
            <Text style={styles.message}>{alert.message}</Text>
            <Text style={styles.meta}>
              Status {alert.status} · {formatTs(alert.created_at)}
            </Text>
            {alert.zone_id ? (
              <Text style={styles.meta}>Zone: {alert.zone_id}</Text>
            ) : null}
            {alert.decision_id ? (
              <Text style={styles.meta}>Decision: {alert.decision_id}</Text>
            ) : null}
          </View>

          {!isOnline ? (
            <Text style={styles.offline}>Controls disabled while offline.</Text>
          ) : null}

          <View style={styles.actions}>
            <Pressable
              style={[styles.btn, styles.secondary, controlsDisabled && styles.disabled]}
              disabled={controlsDisabled}
              onPress={() => void ackMut.mutateAsync()}
            >
              <Text style={styles.secondaryText}>Acknowledge</Text>
            </Pressable>
            <Pressable
              style={[styles.btn, styles.primary, controlsDisabled && styles.disabled]}
              disabled={controlsDisabled}
              onPress={() => void resolveMut.mutateAsync()}
            >
              <Text style={styles.primaryText}>Resolve</Text>
            </Pressable>
          </View>

          {ackMut.error || resolveMut.error ? (
            <Text style={styles.error}>
              {(ackMut.error || resolveMut.error) instanceof Error
                ? ((ackMut.error || resolveMut.error) as Error).message
                : "Action failed"}
            </Text>
          ) : null}
        </>
      ) : null}
    </Screen>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderWidth: 1,
    borderRadius: 10,
    padding: spacing.lg,
  },
  severity: {
    fontSize: 11,
    fontWeight: "800",
    letterSpacing: 0.8,
    textTransform: "uppercase",
    marginBottom: spacing.sm,
  },
  title: {
    color: colors.text,
    fontSize: 20,
    fontWeight: "700",
    marginBottom: spacing.sm,
  },
  message: {
    color: colors.muted,
    fontSize: 14,
    lineHeight: 20,
  },
  meta: {
    marginTop: spacing.sm,
    color: colors.muted,
    fontSize: 12,
  },
  offline: {
    marginTop: spacing.md,
    color: colors.warning,
    fontSize: 13,
  },
  actions: {
    flexDirection: "row",
    gap: spacing.sm,
    marginTop: spacing.lg,
  },
  btn: {
    flex: 1,
    borderRadius: 8,
    paddingVertical: 14,
    alignItems: "center",
  },
  secondary: {
    borderWidth: 1,
    borderColor: colors.border,
  },
  secondaryText: {
    color: colors.text,
    fontWeight: "600",
  },
  primary: {
    backgroundColor: colors.live,
  },
  primaryText: {
    color: colors.bg,
    fontWeight: "700",
  },
  disabled: {
    opacity: 0.45,
  },
  error: {
    marginTop: spacing.md,
    color: colors.critical,
    fontSize: 13,
  },
});
