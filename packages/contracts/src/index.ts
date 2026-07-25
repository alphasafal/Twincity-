import { z } from "zod";

/** Shared TwinPilot domain contracts (Zod). Keep aligned with services/api enums. */

export const OperatingModeSchema = z.enum([
  "AUTONOMOUS",
  "GUARDED",
  "ADVISORY",
  "FALLBACK",
  "MANUAL",
]);
export type OperatingMode = z.infer<typeof OperatingModeSchema>;

export const UserRoleSchema = z.enum([
  "ADMINISTRATOR",
  "FACILITY_MANAGER",
  "OPERATOR",
  "VIEWER",
]);
export type UserRole = z.infer<typeof UserRoleSchema>;

export const AlertSeveritySchema = z.enum([
  "INFORMATIONAL",
  "WARNING",
  "HIGH",
  "CRITICAL",
]);
export type AlertSeverity = z.infer<typeof AlertSeveritySchema>;

export const AlertStatusSchema = z.enum(["OPEN", "ACKNOWLEDGED", "RESOLVED"]);
export type AlertStatus = z.infer<typeof AlertStatusSchema>;

export const PlanStatusSchema = z.enum([
  "CANDIDATE",
  "SIMULATED",
  "VALIDATED",
  "APPROVED",
  "REJECTED",
  "APPLIED",
  "EXPIRED",
]);
export type PlanStatus = z.infer<typeof PlanStatusSchema>;

export const DecisionExecutionStatusSchema = z.enum([
  "PENDING",
  "APPLIED",
  "REJECTED",
  "ROLLED_BACK",
  "MANUAL",
]);
export type DecisionExecutionStatus = z.infer<typeof DecisionExecutionStatusSchema>;

export const WsEventTypeSchema = z.enum([
  "telemetry.updated",
  "telemetry.poll",
  "building.mode_changed",
  "decision.created",
  "control.applied",
  "control.rejected",
  "alert.created",
  "rollback.started",
  "rollback.completed",
]);
export type WsEventType = z.infer<typeof WsEventTypeSchema>;

export const WsEventEnvelopeSchema = z.object({
  event_type: z.string(),
  event_id: z.string(),
  building_id: z.string().optional(),
  timestamp: z.string().nullable().optional(),
  payload: z.record(z.unknown()).default({}),
  schema_version: z.string().default("1.0"),
});
export type WsEventEnvelope = z.infer<typeof WsEventEnvelopeSchema>;

export const TokenResponseSchema = z.object({
  access_token: z.string(),
  refresh_token: z.string(),
  token_type: z.string().default("bearer"),
});
export type TokenResponse = z.infer<typeof TokenResponseSchema>;
