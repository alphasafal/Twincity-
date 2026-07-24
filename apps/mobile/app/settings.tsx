import { useQuery } from "@tanstack/react-query";
import { StyleSheet, Text, View } from "react-native";
import { Screen } from "@/components/Screen";
import { api, getApiBaseUrl } from "@/lib/api";
import { useAuthStore } from "@/lib/auth-store";
import { useOfflineStore } from "@/lib/offline-store";
import { colors, spacing } from "@/lib/theme";
import { formatRelative } from "@/lib/utils";

export default function SettingsScreen() {
  const user = useAuthStore((s) => s.user);
  const building = useAuthStore((s) => s.building);
  const isOnline = useOfflineStore((s) => s.isOnline);
  const lastUpdatedAt = useOfflineStore((s) => s.lastUpdatedAt);

  const healthQuery = useQuery({
    queryKey: ["health"],
    queryFn: () => api.health(),
    enabled: isOnline,
    retry: 0,
  });

  return (
    <Screen title="Settings" subtitle="Mobile client configuration">
      <View style={styles.card}>
        <Text style={styles.label}>API endpoint</Text>
        <Text style={styles.value}>{getApiBaseUrl()}</Text>
        <Text style={styles.meta}>
          Set EXPO_PUBLIC_API_URL (default http://localhost:8000)
        </Text>
      </View>

      <View style={styles.card}>
        <Text style={styles.label}>Connectivity</Text>
        <Text style={styles.value}>{isOnline ? "Online" : "Offline"}</Text>
        <Text style={styles.meta}>
          Cached status updated {formatRelative(lastUpdatedAt)}
        </Text>
      </View>

      <View style={styles.card}>
        <Text style={styles.label}>Session</Text>
        <Text style={styles.value}>{user?.email || "—"}</Text>
        <Text style={styles.meta}>Role: {user?.role || "—"}</Text>
        <Text style={styles.meta}>Building: {building?.name || "—"}</Text>
      </View>

      <View style={styles.card}>
        <Text style={styles.label}>Backend health</Text>
        {healthQuery.isLoading ? (
          <Text style={styles.meta}>Checking…</Text>
        ) : healthQuery.error ? (
          <Text style={styles.error}>
            {healthQuery.error instanceof Error
              ? healthQuery.error.message
              : "Health check failed"}
          </Text>
        ) : (
          <Text style={styles.value}>
            {JSON.stringify(healthQuery.data ?? {}, null, 0).slice(0, 180)}
          </Text>
        )}
      </View>

      <View style={styles.card}>
        <Text style={styles.label}>Demo notes</Text>
        <Text style={styles.meta}>
          Critical alerts use a local notification abstraction that no-ops safely
          when permission is denied.
        </Text>
        <Text style={styles.meta}>
          Offline mode serves the last cached building status and disables
          approval / rollback controls.
        </Text>
      </View>
    </Screen>
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
  label: {
    color: colors.muted,
    fontSize: 11,
    letterSpacing: 0.8,
    textTransform: "uppercase",
    marginBottom: 6,
  },
  value: {
    color: colors.text,
    fontSize: 14,
    fontWeight: "600",
  },
  meta: {
    color: colors.muted,
    fontSize: 13,
    marginTop: 6,
    lineHeight: 18,
  },
  error: {
    color: colors.critical,
    fontSize: 13,
  },
});
