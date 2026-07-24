export type OperatingMode =
  | "AUTONOMOUS"
  | "GUARDED"
  | "ADVISORY"
  | "FALLBACK"
  | "MANUAL";

export type UserRole =
  | "ADMINISTRATOR"
  | "FACILITY_MANAGER"
  | "OPERATOR"
  | "VIEWER";

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface User {
  id: string;
  name: string;
  email: string;
  role: UserRole | string;
  is_active: boolean;
  last_login_at?: string | null;
}

export interface ConfidenceBreakdown {
  score?: number;
  sensor_health?: number;
  data_freshness?: number;
  forecast_confidence?: number;
  simulation_confidence?: number;
  model_accuracy?: number;
  service_health?: number;
  [key: string]: number | undefined;
}

export interface Building {
  id: string;
  name: string;
  location: string;
  timezone: string;
  area_m2: number;
  building_type: string;
  current_mode: OperatingMode | string;
  is_demo: boolean;
  confidence: number;
  autonomy_confidence_json?: ConfidenceBreakdown | null;
}

export interface Zone {
  id: string;
  building_id: string;
  name: string;
  floor: number;
  area_m2: number;
  capacity: number;
  preferred_temperature: number;
  minimum_temperature: number;
  maximum_temperature: number;
  external_key: string;
}

export interface ZoneLiveState {
  temperature?: number;
  humidity?: number;
  co2?: number;
  occupancy_count?: number;
  cooling_setpoint?: number;
  heating_setpoint?: number;
  power_kw?: number;
  comfort_status?: string;
  sensor_health?: number;
  sensor_failed?: boolean;
  data_freshness_seconds?: number;
  estimated_temperature?: number;
  [key: string]: unknown;
}

export interface BuildingState {
  timestamp_iso?: string;
  outdoor_temperature?: number;
  total_building_power_kw?: number;
  electricity_tariff?: number;
  grid_carbon_intensity?: number;
  zones?: Record<string, ZoneLiveState>;
  [key: string]: unknown;
}

export interface KpiHistoryPoint {
  timestamp?: string;
  power_kw?: number;
  baseline_power_kw?: number;
  carbon_intensity?: number;
  comfort_compliance?: number;
  baseline_energy_kwh?: number;
  twin_energy_kwh?: number;
  [key: string]: unknown;
}

export interface BuildingStatus {
  building: Building;
  mode: OperatingMode | string;
  confidence: ConfidenceBreakdown | number | null;
  live_total_load_kw?: number | null;
  energy_saved_today_pct?: number;
  cost_saved_today?: number;
  carbon_avoided_today_kg?: number;
  peak_demand_reduction_pct?: number;
  comfort_compliance_pct?: number;
  healthy_sensors_pct?: number;
  active_alerts?: number;
  pending_decisions?: number;
  state?: BuildingState;
  kpi_history?: KpiHistoryPoint[];
  simulated?: boolean;
  active_scenario?: string | null;
}

export interface ControlPlan {
  id: string;
  plan_name: string;
  source: string;
  status: string;
  objective_score: number;
  predicted_metrics_json?: Record<string, number | string | boolean | null>;
  confidence: number;
  feasibility: boolean;
  actions_json?: Array<Record<string, unknown>>;
  score_breakdown_json?: Record<string, number | string | boolean | null>;
  validation_json?: Record<string, unknown> | null;
  validation_token?: string | null;
  expires_at?: string | null;
  state_hash?: string | null;
  simulation_status?: string;
}

export interface Decision {
  id: string;
  building_id?: string;
  selected_plan_id?: string | null;
  mode: string;
  trigger: string;
  explanation?: string | null;
  confidence: number;
  validation_status: string;
  execution_status: string;
  predicted_metrics_json?: Record<string, unknown> | null;
  realized_metrics_json?: Record<string, unknown> | null;
  prediction_error_json?: Record<string, unknown> | null;
  candidate_plan_ids_json?: string[] | null;
  rejected_plan_ids_json?: string[] | null;
  observed_state_json?: Record<string, unknown> | null;
  goal_profile_json?: Record<string, unknown> | null;
  applied_action_json?: Record<string, unknown> | null;
  rollback_status?: string | null;
  created_at?: string | null;
  executed_at?: string | null;
}

export interface Alert {
  id: string;
  zone_id?: string | null;
  decision_id?: string | null;
  severity: string;
  alert_type: string;
  title: string;
  message: string;
  status: string;
  notes_json?: Array<Record<string, unknown>> | null;
  created_at?: string | null;
}

export interface AssistantAnswer {
  summary?: string;
  explanation?: string;
  confidence?: number;
  citations?: Array<Record<string, unknown>>;
  recommended_actions?: string[];
  [key: string]: unknown;
}

export const DEMO_ACCOUNTS = [
  {
    email: "admin@twinpilot.demo",
    password: "TwinPilot-Admin-Demo!",
    role: "Administrator",
  },
  {
    email: "manager@twinpilot.demo",
    password: "TwinPilot-Manager-Demo!",
    role: "Facility Manager",
  },
  {
    email: "operator@twinpilot.demo",
    password: "TwinPilot-Operator-Demo!",
    role: "Operator",
  },
  {
    email: "viewer@twinpilot.demo",
    password: "TwinPilot-Viewer-Demo!",
    role: "Viewer",
  },
] as const;
