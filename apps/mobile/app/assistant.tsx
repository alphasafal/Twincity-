import { useState } from "react";
import {
  ActivityIndicator,
  FlatList,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { OfflineBanner } from "@/components/OfflineBanner";
import { api } from "@/lib/api";
import { useBuildingId } from "@/lib/hooks";
import { useOfflineStore } from "@/lib/offline-store";
import { colors, spacing } from "@/lib/theme";

type ChatItem = {
  id: string;
  role: "user" | "assistant";
  text: string;
};

export default function AssistantScreen() {
  const buildingId = useBuildingId();
  const isOnline = useOfflineStore((s) => s.isOnline);
  const [message, setMessage] = useState("");
  const [conversationId, setConversationId] = useState<string | undefined>();
  const [items, setItems] = useState<ChatItem[]>([
    {
      id: "welcome",
      role: "assistant",
      text: "Ask about load, comfort, decisions, or why a plan was blocked.",
    },
  ]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const send = async () => {
    const trimmed = message.trim();
    if (!trimmed || !buildingId || busy || !isOnline) return;
    setBusy(true);
    setError(null);
    setMessage("");
    const userItem: ChatItem = {
      id: `u-${Date.now()}`,
      role: "user",
      text: trimmed,
    };
    setItems((prev) => [...prev, userItem]);
    try {
      const res = await api.assistantChat(buildingId, trimmed, conversationId);
      setConversationId(res.conversation_id);
      const answer =
        String(res.answer.summary || res.answer.explanation || "No answer returned.") +
        (res.answer.confidence != null
          ? `\n\nConfidence: ${Math.round(Number(res.answer.confidence) * 100)}%`
          : "");
      setItems((prev) => [
        ...prev,
        { id: `a-${Date.now()}`, role: "assistant", text: answer },
      ]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Assistant request failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <SafeAreaView style={styles.safe} edges={["bottom", "left", "right"]}>
      <KeyboardAvoidingView
        style={styles.flex}
        behavior={Platform.OS === "ios" ? "padding" : undefined}
        keyboardVerticalOffset={80}
      >
        <View style={styles.header}>
          <Text style={styles.brand}>TwinPilot</Text>
          <Text style={styles.title}>Assistant</Text>
          <OfflineBanner />
          {!isOnline ? (
            <Text style={styles.offline}>Chat disabled while offline.</Text>
          ) : null}
          {error ? <Text style={styles.error}>{error}</Text> : null}
        </View>

        <FlatList
          data={items}
          keyExtractor={(item) => item.id}
          contentContainerStyle={styles.list}
          renderItem={({ item }) => (
            <View
              style={[
                styles.bubble,
                item.role === "user" ? styles.userBubble : styles.assistantBubble,
              ]}
            >
              <Text style={styles.bubbleText}>{item.text}</Text>
            </View>
          )}
        />

        <View style={styles.composer}>
          <TextInput
            style={styles.input}
            value={message}
            onChangeText={setMessage}
            placeholder="Ask TwinPilot…"
            placeholderTextColor={colors.muted}
            editable={isOnline && !busy}
            multiline
          />
          <Pressable
            style={[styles.send, (!isOnline || busy || !message.trim()) && styles.disabled]}
            disabled={!isOnline || busy || !message.trim()}
            onPress={() => void send()}
          >
            {busy ? (
              <ActivityIndicator color={colors.bg} />
            ) : (
              <Text style={styles.sendText}>Send</Text>
            )}
          </Pressable>
        </View>
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
  header: {
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.sm,
  },
  brand: {
    color: colors.live,
    fontSize: 11,
    letterSpacing: 2,
    textTransform: "uppercase",
    fontWeight: "700",
  },
  title: {
    color: colors.text,
    fontSize: 22,
    fontWeight: "700",
    marginBottom: spacing.sm,
  },
  offline: {
    color: colors.warning,
    fontSize: 12,
    marginBottom: spacing.sm,
  },
  error: {
    color: colors.critical,
    fontSize: 12,
    marginBottom: spacing.sm,
  },
  list: {
    padding: spacing.lg,
    gap: spacing.sm,
    paddingBottom: spacing.xl,
  },
  bubble: {
    borderRadius: 12,
    padding: spacing.md,
    maxWidth: "92%",
  },
  userBubble: {
    alignSelf: "flex-end",
    backgroundColor: "rgba(34,211,238,0.16)",
    borderColor: colors.live,
    borderWidth: 1,
  },
  assistantBubble: {
    alignSelf: "flex-start",
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderWidth: 1,
  },
  bubbleText: {
    color: colors.text,
    fontSize: 14,
    lineHeight: 20,
  },
  composer: {
    flexDirection: "row",
    gap: spacing.sm,
    padding: spacing.lg,
    borderTopWidth: 1,
    borderTopColor: colors.border,
    backgroundColor: colors.surface,
  },
  input: {
    flex: 1,
    minHeight: 44,
    maxHeight: 120,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.bg,
    borderRadius: 8,
    color: colors.text,
    paddingHorizontal: spacing.md,
    paddingVertical: 10,
  },
  send: {
    backgroundColor: colors.live,
    borderRadius: 8,
    paddingHorizontal: 16,
    alignItems: "center",
    justifyContent: "center",
    minWidth: 72,
  },
  sendText: {
    color: colors.bg,
    fontWeight: "700",
  },
  disabled: {
    opacity: 0.45,
  },
});
