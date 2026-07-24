import { router } from "expo-router";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { DecisionApprovalCard } from "@/components/DecisionApprovalCard";
import { Screen } from "@/components/Screen";
import { api } from "@/lib/api";
import {
  useBuildingId,
  useDecisions,
  useInvalidateBuilding,
} from "@/lib/hooks";
import { useOfflineStore } from "@/lib/offline-store";
import { colors, spacing } from "@/lib/theme";

export default function DecisionsScreen() {
  const buildingId = useBuildingId();
  const isOnline = useOfflineStore((s) => s.isOnline);
  const invalidate = useInvalidateBuilding();
  const { data, isLoading, error, refetch } = useDecisions(buildingId);

  const pending = (data || []).filter(
    (d) => d.execution_status.toUpperCase() === "PENDING",
  );
  const others = (data || []).filter(
    (d) => d.execution_status.toUpperCase() !== "PENDING",
  );

  const actOnPlan = async (
    planId: string | null | undefined,
    action: "approve" | "reject" | "revise",
    reason: string,
  ) => {
    if (!planId) throw new Error("Decision has no selected plan to act on");
    if (action === "approve") await api.approvePlan(planId, reason);
    else if (action === "reject") await api.rejectPlan(planId, reason);
    else await api.requestRevisedPlan(planId, reason);
    invalidate(buildingId);
    await refetch();
  };

  return (
    <Screen
      title="Decisions"
      subtitle="Approve, reject, or request a revised plan"
      loading={isLoading && !data}
      error={error instanceof Error ? error.message : null}
    >
      {!isOnline ? (
        <Text style={styles.offlineHint}>
          Approval controls are disabled while offline.
        </Text>
      ) : null}

      <Text style={styles.section}>Pending approval</Text>
      {pending.map((decision) => (
        <View key={decision.id}>
          <DecisionApprovalCard
            decision={decision}
            disabled={!isOnline}
            onApprove={(reason) =>
              actOnPlan(decision.selected_plan_id, "approve", reason)
            }
            onReject={(reason) =>
              actOnPlan(decision.selected_plan_id, "reject", reason)
            }
            onRequestRevised={(reason) =>
              actOnPlan(decision.selected_plan_id, "revise", reason)
            }
          />
          <Pressable
            style={styles.detailLink}
            onPress={() => router.push(`/decisions/${decision.id}`)}
          >
            <Text style={styles.detailText}>View details</Text>
          </Pressable>
        </View>
      ))}
      {!isLoading && !pending.length ? (
        <Text style={styles.empty}>No pending decisions.</Text>
      ) : null}

      {others.length ? (
        <>
          <Text style={[styles.section, styles.sectionSpaced]}>Recent</Text>
          {others.slice(0, 12).map((decision) => (
            <Pressable
              key={decision.id}
              style={styles.row}
              onPress={() => router.push(`/decisions/${decision.id}`)}
            >
              <Text style={styles.rowTitle} numberOfLines={1}>
                {decision.trigger}
              </Text>
              <Text style={styles.rowMeta}>
                {decision.execution_status} · {decision.mode}
              </Text>
            </Pressable>
          ))}
        </>
      ) : null}
    </Screen>
  );
}

const styles = StyleSheet.create({
  offlineHint: {
    color: colors.warning,
    fontSize: 13,
    marginBottom: spacing.md,
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
  detailLink: {
    marginTop: -4,
    marginBottom: spacing.md,
    paddingVertical: 4,
  },
  detailText: {
    color: colors.live,
    fontWeight: "600",
    fontSize: 13,
  },
  row: {
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderWidth: 1,
    borderRadius: 10,
    padding: spacing.md,
    marginBottom: spacing.sm,
  },
  rowTitle: {
    color: colors.text,
    fontWeight: "600",
    fontSize: 14,
  },
  rowMeta: {
    color: colors.muted,
    fontSize: 12,
    marginTop: 4,
  },
});
