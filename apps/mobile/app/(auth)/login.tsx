import { zodResolver } from "@hookform/resolvers/zod";
import { router } from "expo-router";
import { useState } from "react";
import { Controller, useForm } from "react-hook-form";
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { api } from "@/lib/api";
import { useAuthStore } from "@/lib/auth-store";
import { type LoginFormValues, loginSchema } from "@/lib/login-schema";
import { colors, spacing } from "@/lib/theme";
import { DEMO_ACCOUNTS } from "@/lib/types";

export default function LoginScreen() {
  const setTokens = useAuthStore((s) => s.setTokens);
  const setUser = useAuthStore((s) => s.setUser);
  const setBuilding = useAuthStore((s) => s.setBuilding);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const form = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      email: DEMO_ACCOUNTS[0].email,
      password: DEMO_ACCOUNTS[0].password,
    },
  });

  const onSubmit = form.handleSubmit(async (values) => {
    setLoading(true);
    setError(null);
    try {
      const tokens = await api.login(values.email, values.password);
      await setTokens(tokens.access_token, tokens.refresh_token);
      const me = await api.me();
      await setUser(me);
      const buildings = await api.listBuildings();
      if (buildings[0]) await setBuilding(buildings[0]);
      router.replace("/(tabs)/overview");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  });

  return (
    <SafeAreaView style={styles.safe}>
      <KeyboardAvoidingView
        style={styles.flex}
        behavior={Platform.OS === "ios" ? "padding" : undefined}
      >
        <ScrollView
          contentContainerStyle={styles.content}
          keyboardShouldPersistTaps="handled"
        >
          <Text style={styles.brand}>TwinPilot</Text>
          <Text style={styles.title}>TwinPilot</Text>
          <Text style={styles.tagline}>Autonomous optimization you can verify.</Text>
          <Text style={styles.copy}>
            Mobile control room for live telemetry, Safety Shield decisions, and
            constrained rollback.
          </Text>

          <View style={styles.panel}>
            <Text style={styles.panelTitle}>Sign in</Text>
            <Text style={styles.panelHint}>Demo credentials for local development.</Text>

            <Text style={styles.label}>Email</Text>
            <Controller
              control={form.control}
              name="email"
              render={({ field: { onChange, onBlur, value } }) => (
                <TextInput
                  style={styles.input}
                  autoCapitalize="none"
                  autoCorrect={false}
                  keyboardType="email-address"
                  autoComplete="username"
                  placeholder="email@twinpilot.demo"
                  placeholderTextColor={colors.muted}
                  onBlur={onBlur}
                  onChangeText={onChange}
                  value={value}
                />
              )}
            />
            {form.formState.errors.email ? (
              <Text style={styles.fieldError}>{form.formState.errors.email.message}</Text>
            ) : null}

            <Text style={styles.label}>Password</Text>
            <Controller
              control={form.control}
              name="password"
              render={({ field: { onChange, onBlur, value } }) => (
                <TextInput
                  style={styles.input}
                  secureTextEntry
                  autoComplete="password"
                  placeholder="Password"
                  placeholderTextColor={colors.muted}
                  onBlur={onBlur}
                  onChangeText={onChange}
                  value={value}
                />
              )}
            />
            {form.formState.errors.password ? (
              <Text style={styles.fieldError}>
                {form.formState.errors.password.message}
              </Text>
            ) : null}

            <Text style={styles.demoLabel}>Demo account</Text>
            <View style={styles.demoGrid}>
              {DEMO_ACCOUNTS.slice(0, 3).map((account) => {
                const active = form.watch("email") === account.email;
                return (
                  <Pressable
                    key={account.email}
                    style={[styles.demoBtn, active && styles.demoBtnActive]}
                    onPress={() => {
                      form.setValue("email", account.email);
                      form.setValue("password", account.password);
                    }}
                  >
                    <Text style={styles.demoRole}>{account.role}</Text>
                    <Text style={styles.demoEmail} numberOfLines={1}>
                      {account.email}
                    </Text>
                  </Pressable>
                );
              })}
            </View>

            {error ? (
              <View style={styles.errorBox}>
                <Text style={styles.errorText}>{error}</Text>
              </View>
            ) : null}

            <Pressable
              style={[styles.submit, loading && styles.disabled]}
              disabled={loading}
              onPress={() => void onSubmit()}
            >
              {loading ? (
                <ActivityIndicator color={colors.bg} />
              ) : (
                <Text style={styles.submitText}>Enter control room</Text>
              )}
            </Pressable>
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: {
    flex: 1,
    backgroundColor: colors.bg,
  },
  flex: {
    flex: 1,
  },
  content: {
    padding: spacing.xl,
    paddingBottom: spacing.xxl,
  },
  brand: {
    color: colors.live,
    fontSize: 12,
    letterSpacing: 3,
    textTransform: "uppercase",
    fontWeight: "700",
  },
  title: {
    marginTop: spacing.sm,
    color: colors.text,
    fontSize: 36,
    fontWeight: "700",
    letterSpacing: -0.5,
  },
  tagline: {
    marginTop: spacing.sm,
    color: colors.text,
    fontSize: 17,
    fontWeight: "500",
  },
  copy: {
    marginTop: spacing.sm,
    color: colors.muted,
    fontSize: 14,
    lineHeight: 20,
    marginBottom: spacing.xl,
  },
  panel: {
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderWidth: 1,
    borderRadius: 12,
    padding: spacing.lg,
  },
  panelTitle: {
    color: colors.text,
    fontSize: 18,
    fontWeight: "700",
  },
  panelHint: {
    color: colors.muted,
    fontSize: 13,
    marginTop: 4,
    marginBottom: spacing.lg,
  },
  label: {
    color: colors.muted,
    fontSize: 13,
    marginBottom: 6,
  },
  input: {
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.bg,
    borderRadius: 8,
    color: colors.text,
    paddingHorizontal: spacing.md,
    paddingVertical: 12,
    marginBottom: spacing.md,
  },
  fieldError: {
    color: colors.critical,
    fontSize: 12,
    marginTop: -8,
    marginBottom: spacing.md,
  },
  demoLabel: {
    color: colors.muted,
    fontSize: 11,
    letterSpacing: 1,
    textTransform: "uppercase",
    marginBottom: spacing.sm,
  },
  demoGrid: {
    gap: spacing.sm,
    marginBottom: spacing.md,
  },
  demoBtn: {
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.bg,
    borderRadius: 8,
    padding: spacing.md,
  },
  demoBtnActive: {
    borderColor: "rgba(34,211,238,0.5)",
    backgroundColor: "rgba(34,211,238,0.1)",
  },
  demoRole: {
    color: colors.text,
    fontWeight: "600",
    fontSize: 13,
  },
  demoEmail: {
    color: colors.muted,
    fontSize: 11,
    marginTop: 2,
    fontVariant: ["tabular-nums"],
  },
  errorBox: {
    borderWidth: 1,
    borderColor: colors.critical,
    backgroundColor: "rgba(248,113,113,0.12)",
    borderRadius: 8,
    padding: spacing.md,
    marginBottom: spacing.md,
  },
  errorText: {
    color: colors.critical,
    fontSize: 13,
  },
  submit: {
    backgroundColor: colors.live,
    borderRadius: 8,
    paddingVertical: 14,
    alignItems: "center",
  },
  submitText: {
    color: colors.bg,
    fontWeight: "700",
    fontSize: 14,
  },
  disabled: {
    opacity: 0.6,
  },
});
