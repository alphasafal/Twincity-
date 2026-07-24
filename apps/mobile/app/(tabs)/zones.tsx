import { router } from "expo-router";
import { StyleSheet, Text, View } from "react-native";
import { Screen } from "@/components/Screen";
import { ZoneListItem } from "@/components/ZoneListItem";
import { useBuildingId, useBuildingStatus, useZones } from "@/lib/hooks";
import { colors, spacing } from "@/lib/theme";
import type { ZoneLiveState } from "@/lib/types";

export default function ZonesScreen() {
  const buildingId = useBuildingId();
  const zonesQuery = useZones(buildingId);
  const statusQuery = useBuildingStatus(buildingId);
  const liveZones = statusQuery.data?.state?.zones || {};

  return (
    <Screen
      title="Zones"
      subtitle="Live comfort and sensor health by zone"
      loading={zonesQuery.isLoading && !zonesQuery.data}
      error={
        zonesQuery.error instanceof Error ? zonesQuery.error.message : null
      }
    >
      {statusQuery.data?.simulated ? (
        <View style={styles.simBanner}>
          <Text style={styles.simText}>Simulated data</Text>
        </View>
      ) : null}

      {(zonesQuery.data || []).map((zone) => {
        const live = (liveZones[zone.external_key] ||
          liveZones[zone.id] ||
          {}) as ZoneLiveState;
        return (
          <ZoneListItem
            key={zone.id}
            name={zone.name}
            floor={zone.floor}
            temperature={
              typeof live.temperature === "number"
                ? live.temperature
                : typeof live.estimated_temperature === "number"
                  ? live.estimated_temperature
                  : null
            }
            comfortStatus={
              typeof live.comfort_status === "string" ? live.comfort_status : null
            }
            sensorHealth={
              typeof live.sensor_health === "number" ? live.sensor_health : null
            }
            onPress={() => router.push(`/zones/${zone.id}`)}
          />
        );
      })}

      {!zonesQuery.isLoading && !(zonesQuery.data || []).length ? (
        <Text style={styles.empty}>No zones available for this building.</Text>
      ) : null}
    </Screen>
  );
}

const styles = StyleSheet.create({
  simBanner: {
    alignSelf: "flex-start",
    backgroundColor: "rgba(251,191,36,0.12)",
    borderColor: colors.warning,
    borderWidth: 1,
    borderRadius: 6,
    paddingHorizontal: 10,
    paddingVertical: 4,
    marginBottom: spacing.md,
  },
  simText: {
    color: colors.warning,
    fontSize: 11,
    fontWeight: "700",
    letterSpacing: 0.6,
    textTransform: "uppercase",
  },
  empty: {
    color: colors.muted,
    fontSize: 14,
    marginTop: spacing.lg,
  },
});
