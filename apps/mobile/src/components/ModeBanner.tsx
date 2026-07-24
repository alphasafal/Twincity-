import { StyleSheet, Text, View } from "react-native";
import { colors, spacing } from "@/lib/theme";

const COPY: Record<string, { title: string; body: string; color: string; bg: string }> = {
  GUARDED: {
    title: "Guarded autonomy",
    body: "Low-risk actions may apply; Safety Shield still blocks high-risk changes.",
    color: colors.live,
    bg: "rgba(34,211,238,0.12)",
  },
  ADVISORY: {
    title: "Advisory mode",
    body: "Plans require explicit human approval before apply.",
    color: colors.warning,
    bg: "rgba(251,191,36,0.12)",
  },
  FALLBACK: {
    title: "Fallback mode",
    body: "Autonomy restricted. Critical alerts or service issues may be blocking optimization.",
    color: colors.critical,
    bg: "rgba(248,113,113,0.12)",
  },
};

export function ModeBanner({ mode }: { mode?: string | null }) {
  const key = (mode || "").toUpperCase();
  const cfg = COPY[key];
  if (!cfg) return null;

  return (
    <View style={[styles.banner, { borderColor: cfg.color, backgroundColor: cfg.bg }]}>
      <Text style={[styles.title, { color: cfg.color }]}>{cfg.title}</Text>
      <Text style={[styles.body, { color: cfg.color }]}>{cfg.body}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  banner: {
    borderWidth: 1,
    borderRadius: 10,
    padding: spacing.md,
    marginBottom: spacing.md,
  },
  title: {
    fontWeight: "700",
    fontSize: 14,
    marginBottom: 4,
  },
  body: {
    fontSize: 13,
    opacity: 0.9,
    lineHeight: 18,
  },
});
