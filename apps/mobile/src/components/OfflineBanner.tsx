import { StyleSheet, Text, View } from "react-native";
import { useOfflineStore } from "@/lib/offline-store";
import { colors, spacing } from "@/lib/theme";
import { formatRelative } from "@/lib/utils";

export function OfflineBanner() {
  const isOnline = useOfflineStore((s) => s.isOnline);
  const lastUpdatedAt = useOfflineStore((s) => s.lastUpdatedAt);

  if (isOnline) {
    if (!lastUpdatedAt) return null;
    return (
      <View style={styles.online}>
        <Text style={styles.onlineText}>Last updated {formatRelative(lastUpdatedAt)}</Text>
      </View>
    );
  }

  return (
    <View style={styles.offline}>
      <Text style={styles.offlineTitle}>Offline — showing cached status</Text>
      <Text style={styles.offlineBody}>
        Last updated {formatRelative(lastUpdatedAt)}. Controls are disabled until connectivity
        returns.
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  online: {
    paddingVertical: 6,
    marginBottom: spacing.sm,
  },
  onlineText: {
    color: colors.muted,
    fontSize: 11,
  },
  offline: {
    backgroundColor: "rgba(251,191,36,0.12)",
    borderColor: colors.warning,
    borderWidth: 1,
    borderRadius: 10,
    padding: spacing.md,
    marginBottom: spacing.md,
  },
  offlineTitle: {
    color: colors.warning,
    fontWeight: "700",
    fontSize: 13,
    marginBottom: 4,
  },
  offlineBody: {
    color: colors.warning,
    fontSize: 12,
    opacity: 0.9,
    lineHeight: 17,
  },
});
