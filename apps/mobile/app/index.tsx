import { Redirect } from "expo-router";
import { ActivityIndicator, StyleSheet, View } from "react-native";
import { useRequireAuth } from "@/lib/hooks";
import { colors } from "@/lib/theme";

export default function IndexScreen() {
  const { hydrated, isAuthenticated } = useRequireAuth();

  if (!hydrated) {
    return (
      <View style={styles.boot}>
        <ActivityIndicator color={colors.live} />
      </View>
    );
  }

  if (isAuthenticated) {
    return <Redirect href="/(tabs)/overview" />;
  }

  return <Redirect href="/(auth)/login" />;
}

const styles = StyleSheet.create({
  boot: {
    flex: 1,
    backgroundColor: colors.bg,
    alignItems: "center",
    justifyContent: "center",
  },
});
