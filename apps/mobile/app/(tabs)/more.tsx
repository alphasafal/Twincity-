import { router } from "expo-router";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { Screen } from "@/components/Screen";
import { api, getApiBaseUrl } from "@/lib/api";
import { useAuthStore } from "@/lib/auth-store";
import { colors, spacing } from "@/lib/theme";

export default function MoreScreen() {
  const user = useAuthStore((s) => s.user);
  const building = useAuthStore((s) => s.building);
  const logout = useAuthStore((s) => s.logout);

  const onLogout = async () => {
    try {
      await api.logout();
    } catch {
      // Local logout still proceeds.
    }
    await logout();
    router.replace("/(auth)/login");
  };

  return (
    <Screen title="More" subtitle="Account, assistant, and settings">
      <View style={styles.card}>
        <Text style={styles.label}>Signed in</Text>
        <Text style={styles.value}>{user?.name || "—"}</Text>
        <Text style={styles.meta}>{user?.email}</Text>
        <Text style={styles.meta}>Role: {user?.role || "—"}</Text>
      </View>

      <View style={styles.card}>
        <Text style={styles.label}>Building</Text>
        <Text style={styles.value}>{building?.name || "—"}</Text>
        <Text style={styles.meta}>{building?.location || "No building selected"}</Text>
        {building?.is_demo ? (
          <Text style={styles.sim}>Simulated demo building</Text>
        ) : null}
      </View>

      <MenuRow label="Operations assistant" onPress={() => router.push("/assistant")} />
      <MenuRow label="Settings" onPress={() => router.push("/settings")} />

      <View style={styles.card}>
        <Text style={styles.label}>API</Text>
        <Text style={styles.meta}>{getApiBaseUrl()}</Text>
      </View>

      <Pressable style={styles.logout} onPress={() => void onLogout()}>
        <Text style={styles.logoutText}>Sign out</Text>
      </Pressable>
    </Screen>
  );
}

function MenuRow({ label, onPress }: { label: string; onPress: () => void }) {
  return (
    <Pressable
      style={({ pressed }) => [styles.row, pressed && styles.pressed]}
      onPress={onPress}
    >
      <Text style={styles.rowLabel}>{label}</Text>
      <Text style={styles.chevron}>›</Text>
    </Pressable>
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
    fontSize: 16,
    fontWeight: "700",
  },
  meta: {
    color: colors.muted,
    fontSize: 13,
    marginTop: 4,
  },
  sim: {
    marginTop: spacing.sm,
    color: colors.warning,
    fontSize: 11,
    fontWeight: "700",
    textTransform: "uppercase",
  },
  row: {
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderWidth: 1,
    borderRadius: 10,
    padding: spacing.md,
    marginBottom: spacing.sm,
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  pressed: {
    opacity: 0.85,
  },
  rowLabel: {
    color: colors.text,
    fontWeight: "600",
    fontSize: 15,
  },
  chevron: {
    color: colors.live,
    fontSize: 22,
    fontWeight: "300",
  },
  logout: {
    marginTop: spacing.lg,
    borderWidth: 1,
    borderColor: colors.critical,
    backgroundColor: "rgba(248,113,113,0.12)",
    borderRadius: 10,
    paddingVertical: 14,
    alignItems: "center",
  },
  logoutText: {
    color: colors.critical,
    fontWeight: "800",
  },
});
