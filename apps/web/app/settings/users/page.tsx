"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import {
  EmptyState,
  PageHeader,
  Panel,
  SettingsSubnav,
} from "@/components/AppShell";
import { api, ApiError } from "@/lib/api";
import { useAuthStore } from "@/lib/auth-store";
import { formatTs } from "@/lib/utils";

const ROLES = ["ADMINISTRATOR", "FACILITY_MANAGER", "OPERATOR", "VIEWER"] as const;

export default function UsersSettingsPage() {
  const role = useAuthStore((s) => s.user?.role);
  const isAdmin = role === "ADMINISTRATOR";
  const qc = useQueryClient();

  const { data = [], isLoading, error } = useQuery({
    queryKey: ["users"],
    queryFn: () => api.listUsers(),
    enabled: isAdmin,
  });

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [newRole, setNewRole] = useState<(typeof ROLES)[number]>("VIEWER");
  const [reason, setReason] = useState("Invite demo operator");
  const [message, setMessage] = useState<string | null>(null);

  const invite = useMutation({
    mutationFn: () =>
      api.createUser({
        name,
        email,
        password,
        role: newRole,
        reason,
      }),
    onSuccess: async () => {
      setMessage("User created.");
      setName("");
      setEmail("");
      setPassword("");
      await qc.invalidateQueries({ queryKey: ["users"] });
    },
    onError: (err) => {
      setMessage(err instanceof ApiError ? String(err.message) : "Invite failed");
    },
  });

  const toggleActive = useMutation({
    mutationFn: (args: { id: string; is_active: boolean }) =>
      api.updateUser(args.id, {
        is_active: args.is_active,
        reason: args.is_active ? "Reactivated user" : "Deactivated user",
      }),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["users"] });
    },
  });

  return (
    <div>
      <PageHeader
        title="Users"
        description="Directory and invites via /api/v1/users (administrator only)."
      />
      <SettingsSubnav />

      {!isAdmin ? (
        <EmptyState>
          User management requires the ADMINISTRATOR role.
        </EmptyState>
      ) : null}

      {isAdmin && isLoading ? <EmptyState>Loading users…</EmptyState> : null}
      {isAdmin && error ? (
        <EmptyState>{error instanceof Error ? error.message : "Failed to load users"}</EmptyState>
      ) : null}

      {isAdmin ? (
        <Panel className="mb-4 p-4">
          <h3 className="text-sm font-semibold">Invite user</h3>
          <div className="mt-3 grid gap-3 sm:grid-cols-2">
            <input
              placeholder="Name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="rounded-md border border-border bg-background px-3 py-2 text-sm"
            />
            <input
              placeholder="Email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="rounded-md border border-border bg-background px-3 py-2 text-sm"
            />
            <input
              placeholder="Temporary password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="rounded-md border border-border bg-background px-3 py-2 text-sm"
            />
            <select
              value={newRole}
              onChange={(e) => setNewRole(e.target.value as (typeof ROLES)[number])}
              className="rounded-md border border-border bg-background px-3 py-2 text-sm"
            >
              {ROLES.map((r) => (
                <option key={r} value={r}>
                  {r}
                </option>
              ))}
            </select>
            <input
              placeholder="Audit reason"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              className="rounded-md border border-border bg-background px-3 py-2 text-sm sm:col-span-2"
            />
          </div>
          <button
            type="button"
            disabled={
              invite.isPending ||
              name.trim().length < 2 ||
              email.trim().length < 5 ||
              password.length < 8 ||
              reason.trim().length < 3
            }
            onClick={() => {
              setMessage(null);
              invite.mutate();
            }}
            className="mt-3 rounded-md bg-live px-3 py-2 text-sm font-semibold text-graphite-950 disabled:opacity-50"
          >
            {invite.isPending ? "Creating…" : "Invite user"}
          </button>
          {message ? <p className="mt-2 text-xs text-muted">{message}</p> : null}
        </Panel>
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
                <th className="px-3 py-2">Actions</th>
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
                  <td className="px-3 py-2.5">
                    <button
                      type="button"
                      disabled={toggleActive.isPending}
                      onClick={() =>
                        toggleActive.mutate({ id: user.id, is_active: !user.is_active })
                      }
                      className="rounded border border-border px-2 py-1 text-xs text-muted hover:text-foreground"
                    >
                      {user.is_active ? "Deactivate" : "Activate"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Panel>
      ) : null}
    </div>
  );
}
