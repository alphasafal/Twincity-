import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { type ReactNode, useEffect, useState } from "react";
import { api } from "./api";
import { useAuthStore } from "./auth-store";
import { useNetworkMonitor } from "./hooks";
import { configureNotifications } from "./notifications";

function NetworkBridge({ children }: { children: ReactNode }) {
  useNetworkMonitor();
  return <>{children}</>;
}

function AuthBootstrap({ children }: { children: ReactNode }) {
  const hydrated = useAuthStore((s) => s.hydrated);
  const accessToken = useAuthStore((s) => s.accessToken);
  const setUser = useAuthStore((s) => s.setUser);
  const setBuilding = useAuthStore((s) => s.setBuilding);
  const logout = useAuthStore((s) => s.logout);
  const building = useAuthStore((s) => s.building);

  useEffect(() => {
    void configureNotifications();
  }, []);

  useEffect(() => {
    if (!hydrated || !accessToken) return;
    let cancelled = false;
    (async () => {
      try {
        const me = await api.me();
        if (cancelled) return;
        await setUser(me);
        if (!building) {
          const buildings = await api.listBuildings();
          if (!cancelled && buildings[0]) await setBuilding(buildings[0]);
        }
      } catch {
        if (!cancelled) await logout();
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [hydrated, accessToken, setUser, setBuilding, logout, building]);

  return <>{children}</>;
}

export function AppProviders({ children }: { children: ReactNode }) {
  const [client] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            retry: 1,
            staleTime: 10_000,
          },
        },
      }),
  );

  return (
    <QueryClientProvider client={client}>
      <NetworkBridge>
        <AuthBootstrap>{children}</AuthBootstrap>
      </NetworkBridge>
    </QueryClientProvider>
  );
}
