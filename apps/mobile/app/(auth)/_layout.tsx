import { Redirect, Stack } from "expo-router";
import { useRequireAuth } from "@/lib/hooks";
import { colors } from "@/lib/theme";

export default function AuthLayout() {
  const { hydrated, isAuthenticated } = useRequireAuth();

  if (hydrated && isAuthenticated) {
    return <Redirect href="/(tabs)/overview" />;
  }

  return (
    <Stack
      screenOptions={{
        headerShown: false,
        contentStyle: { backgroundColor: colors.bg },
      }}
    />
  );
}
