import * as Notifications from "expo-notifications";
import { Platform } from "react-native";

let configured = false;
let permissionGranted: boolean | null = null;

/**
 * Demo-safe local notification helpers.
 * Permission failures and unsupported platforms become no-ops.
 */
export async function configureNotifications(): Promise<boolean> {
  if (configured) return Boolean(permissionGranted);
  configured = true;

  try {
    Notifications.setNotificationHandler({
      handleNotification: async () => ({
        shouldShowAlert: true,
        shouldPlaySound: false,
        shouldSetBadge: false,
      }),
    });

    if (Platform.OS === "android") {
      await Notifications.setNotificationChannelAsync("critical-alerts", {
        name: "Critical alerts",
        importance: Notifications.AndroidImportance.HIGH,
      });
    }

    const current = await Notifications.getPermissionsAsync();
    let status = current.status;
    if (status !== "granted") {
      const requested = await Notifications.requestPermissionsAsync();
      status = requested.status;
    }
    permissionGranted = status === "granted";
    return permissionGranted;
  } catch {
    permissionGranted = false;
    return false;
  }
}

export async function notifyCriticalAlert(title: string, body: string): Promise<void> {
  try {
    const ok = await configureNotifications();
    if (!ok) return;
    await Notifications.scheduleNotificationAsync({
      content: {
        title: `TwinPilot · ${title}`,
        body,
        data: { kind: "critical_alert" },
      },
      trigger: null,
    });
  } catch {
    // Demo abstraction: never throw from notification path.
  }
}
