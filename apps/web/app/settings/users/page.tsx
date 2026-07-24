"use client";

import { useQuery } from "@tanstack/react-query";
import {
  EmptyState,
  PageHeader,
  Panel,
  SettingsSubnav,
} from "@/components/AppShell";
import { api } from "@/lib/api";
import { useAuthStore } from "@/lib/auth-store";
import { formatTs } from "@/lib/utils";

export default function UsersSettingsPage() {
  const role = useAuthStore((s) => s.user?.role);
  const isAdmin = role === "ADMINISTRATOR";

  const { data = [], isLoading, error } = useQuery({
    queryKey: ["users"],
    queryFn: () => api.listUsers(),
    enabled: isAdmin,
  });

  return (
    <div>
      <PageHeader
        title="Users"
        description="Directory from /api/v1/users (administrator only)."
      />
      <SettingsSubnav />

      {!isAdmin ? (
        <EmptyState>
          User listing requires the ADMINISTRATOR role. Invite / role-edit controls are not
          implemented by the API yet.
        </EmptyState>
      ) : null}

      {isAdmin && isLoading ? <EmptyState>Loading users…</EmptyState> : null}
      {isAdmin && error ? (
        <EmptyState>{error instanceof Error ? error.message : "Failed to load users"}</EmptyState>
      ) : null}

      {isAdmin && data.length ? (
        <Panel className="overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead className="bg-surface-muted/50 text-[11px] uppercase tracking-wider text-muted">
              <tr>
                <th className="px-3 py-2">Name</th>
                <th className="px-3 py-2">Email</th>
                <th className="px-3 py-2">Role</th>
                <th className="px-3 py-2">Active</th>
                <th className="px-3 py-2">Last login</th>
              </tr>
            </thead>
            <tbody>
              {data.map((user) => (
                <tr key={user.id} className="border-t border-border">
                  <td className="px-3 py-2.5">{user.name}</td>
                  <td className="px-3 py-2.5 font-mono text-xs">{user.email}</td>
                  <td className="px-3 py-2.5 font-mono text-xs">{user.role}</td>
                  <td className="px-3 py-2.5">{user.is_active ? "Yes" : "No"}</td>
                  <td className="px-3 py-2.5 text-xs text-muted">
                    {formatTs(user.last_login_at)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="border-t border-border px-3 py-3">
            <button
              type="button"
              disabled
              className="cursor-not-allowed rounded-md border border-border px-3 py-1.5 text-xs text-muted opacity-50"
            >
              Invite user (unavailable — no API)
            </button>
          </div>
        </Panel>
      ) : null}
    </div>
  );
}
