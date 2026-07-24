import { useQuery } from "@tanstack/react-query";
import { useLocalSearchParams } from "expo-router";
import { StyleSheet, Text, View } from "react-native";
import { DecisionApprovalCard } from "@/components/DecisionApprovalCard";
import { Screen } from "@/components/Screen";
import { api } from "@/lib/api";
import { useBuildingId, useInvalidateBuilding } from "@/lib/hooks";
import { useOfflineStore } from "@/lib/offline-store";
import { colors, spacing } from "@/lib/theme";
import { formatPct, formatTs } from "@/lib/utils";

export default function DecisionDetailScreen() {
  const { decisionId } = useLocalSearchParams<{ decisionId: string }>();
  const buildingId = useBuildingId();
  const isOnline = useOfflineStore((s) => s.isOnline);
  const invalidate = useInvalidateBuilding();

  const decisionQuery = useQuery({
    queryKey: ["decision", decisionId],
    queryFn: () => api.getDecision(decisionId!),
    enabled: Boolean(decisionId) && isOnline,
  });
  const explainQuery = useQuery({
    queryKey: ["decision-explain", decisionId],
    queryFn: () => api.explainDecision(decisionId!),
    enabled: Boolean(decisionId) && isOnline,
  });
  const planQuery = useQuery({
    queryKey: ["plan", decisionQuery.data?.selected_plan_id],
    queryFn: () => api.getPlan(decisionQuery.data!.selected_plan_id!),
    enabled: Boolean(decisionQuery.data?.selected_plan_id) && isOnline,
  });

  const decision = decisionQuery.data;

  const actOnPlan = async (
    action: "approve" | "reject" | "revise",
    reason: string,
  ) => {
    const planId = decision?.selected_plan_id;
    if (!planId) throw new Error("Decision has no selected plan to act on");
    if (action === "approve") await api.approvePlan(planId, reason);
    else if (action === "reject") await api.rejectPlan(planId, reason);
    else await api.requestRevisedPlan(planId, reason);
    invalidate(buildingId);
    await decisionQuery.refetch();
  };

  return (
    <Screen
      title="Decision"
      subtitle={decision?.trigger || "Decision detail"}
      loading={decisionQuery.isLoading && !decision}
      error={
        decisionQuery.error instanceof Error ? decisionQuery.error.message : null
      }
    >
      {decision ? (
        <>
          <DecisionApprovalCard
            decision={decision}
            disabled={!isOnline}
            onApprove={(reason) => actOnPlan("approve", reason)}
            onReject={(reason) => actOnPlan("reject", reason)}
            onRequestRevised={(reason) => actOnPlan("revise", reason)}
          />

          <View style={styles.card}>
            <Text style={styles.label}>Ledger</Text>
            <Text style={styles.row}>
              Validation: {decision.validation_status}
            </Text>
            <Text style={styles.row}>
              Execution: {decision.execution_status}
            </Text>
            <Text style={styles.row}>
              Confidence: {formatPct(decision.confidence * 100, 0)}
            </Text>
            <Text style={styles.row}>Created: {formatTs(decision.created_at)}</Text>
            {decision.rollback_status ? (
              <Text style={styles.row}>Rollback: {decision.rollback_status}</Text>
            ) : null}
          </View>

          {planQuery.data ? (
            <View style={styles.card}>
              <Text style={styles.label}>Selected plan</Text>
              <Text style={styles.title}>{planQuery.data.plan_name}</Text>
              <Text style={styles.row}>
                Status {planQuery.data.status} · Feasible{" "}
                {planQuery.data.feasibility ? "yes" : "no"}
              </Text>
              <Text style={styles.row}>
                Objective score {formatNumberSafe(planQuery.data.objective_score)}
              </Text>
              {planQuery.data.actions_json?.length ? (
                <Text style={styles.row}>
                  {planQuery.data.actions_json.length} proposed actions
                </Text>
              ) : null}
            </View>
          ) : null}

          {explainQuery.data ? (
            <View style={styles.card}>
              <Text style={styles.label}>Explanation</Text>
              <Text style={styles.body}>
                {String(
                  explainQuery.data.summary ||
                    explainQuery.data.explanation ||
                    decision.explanation ||
                    "No explanation available.",
                )}
              </Text>
              {explainQuery.data.recommended_actions?.length ? (
                <View style={styles.actionsList}>
                  {explainQuery.data.recommended_actions.map((item) => (
                    <Text key={item} style={styles.actionItem}>
                      • {item}
                    </Text>
                  ))}
                </View>
              ) : null}
            </View>
          ) : null}
        </>
      ) : null}
    </Screen>
  );
}

function formatNumberSafe(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return "—";
  return value.toFixed(2);
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
    marginBottom: spacing.sm,
  },
  title: {
    color: colors.text,
    fontWeight: "700",
    fontSize: 15,
    marginBottom: 4,
  },
  row: {
    color: colors.muted,
    fontSize: 13,
    marginBottom: 4,
  },
  body: {
    color: colors.text,
    fontSize: 14,
    lineHeight: 20,
  },
  actionsList: {
    marginTop: spacing.md,
    gap: 4,
  },
  actionItem: {
    color: colors.muted,
    fontSize: 13,
  },
});
