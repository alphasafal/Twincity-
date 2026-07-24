"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useEffect, useState, type ReactNode } from "react";
import { api } from "./api";
import { useAuthStore } from "./auth-store";

function AuthBootstrap({ children }: { children: ReactNode }) {
  const hydrated = useAuthStore((s) => s.hydrated);
  const accessToken = useAuthStore((s) => s.accessToken);
  const setUser = useAuthStore((s) => s.setUser);
  const setBuilding = useAuthStore((s) => s.setBuilding);
  const setOrganization = useAuthStore((s) => s.setOrganization);
  const logout = useAuthStore((s) => s.logout);
  const building = useAuthStore((s) => s.building);
  const organization = useAuthStore((s) => s.organization);

  useEffect(() => {
    if (!hydrated || !accessToken) return;
    let cancelled = false;
    (async () => {
      try {
        const me = await api.me();
        if (cancelled) return;
        setUser(me);
        const orgs = await api.listOrganizations();
        if (!cancelled && orgs[0] && !organization) setOrganization(orgs[0]);
        if (!building) {
          const buildings = await api.listBuildings();
          if (!cancelled && buildings[0]) setBuilding(buildings[0]);
        }
      } catch {
        if (!cancelled) logout();
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [
    hydrated,
    accessToken,
    setUser,
    setBuilding,
    setOrganization,
    logout,
    building,
    organization,
  ]);

  return <>{children}</>;
}

export function AppProviders({ children }: { children: ReactNode }) {
  const [client] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 5_000,
            retry: 1,
            refetchOnWindowFocus: false,
          },
        },
      }),
  );

  return (
    <QueryClientProvider client={client}>
      <AuthBootstrap>{children}</AuthBootstrap>
    </QueryClientProvider>
  );
}
