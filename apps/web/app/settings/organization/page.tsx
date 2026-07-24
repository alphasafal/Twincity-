"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { EmptyState, PageHeader, Panel, SettingsSubnav } from "@/components/AppShell";
import { api } from "@/lib/api";
import { useAuthStore } from "@/lib/auth-store";

export default function OrganizationSettingsPage() {
  const organizationId = useAuthStore((s) => s.organizationId);
  const organization = useAuthStore((s) => s.organization);
  const queryClient = useQueryClient();
  const [email, setEmail] = useState("");
  const [role, setRole] = useState("VIEWER");
  const [inviteToken, setInviteToken] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const members = useQuery({
    queryKey: ["org-members", organizationId],
    queryFn: () => api.listOrgMembers(organizationId!),
    enabled: Boolean(organizationId),
  });

  const invite = useMutation({
    mutationFn: () =>
      api.inviteMember(organizationId!, {
        email,
        org_role: role,
        reason: "Invite from organization settings",
      }),
    onSuccess: (result) => {
      setInviteToken(result.token || null);
      setMessage(`Invitation created for ${result.email}`);
      setEmail("");
      void queryClient.invalidateQueries({ queryKey: ["org-members", organizationId] });
    },
    onError: (err) =>
      setMessage(err instanceof Error ? err.message : "Invite failed"),
  });

  const exportAudit = useMutation({
    mutationFn: () => api.exportOrgAudit(organizationId!),
    onSuccess: (result) => {
      const blob = new Blob([JSON.stringify(result, null, 2)], {
        type: "application/json",
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `twinpilot-audit-${organizationId}.json`;
      a.click();
      URL.revokeObjectURL(url);
      setMessage(`Exported ${result.count} immutable audit events`);
    },
    onError: (err) =>
      setMessage(err instanceof Error ? err.message : "Export failed"),
  });

  if (!organizationId) {
    return (
      <div>
        <PageHeader title="Organization" />
        <SettingsSubnav />
        <EmptyState>No organization in session.</EmptyState>
      </div>
    );
  }

  return (
    <div>
      <PageHeader
        title="Organization"
        description={`${organization?.name || "Org"} · plan ${organization?.plan_code || "—"}`}
      />
      <SettingsSubnav />

      <div className="grid gap-4 lg:grid-cols-2">
        <Panel className="p-4">
          <h2 className="mb-3 text-sm font-semibold">Members</h2>
          <ul className="space-y-2 text-sm">
            {(members.data || []).map((m) => (
              <li key={m.id} className="flex justify-between border-b border-border py-2">
                <span>{m.user?.email || m.user_id}</span>
                <span className="text-xs text-muted">{m.org_role}</span>
              </li>
            ))}
          </ul>
        </Panel>
        <Panel className="p-4">
          <h2 className="mb-3 text-sm font-semibold">Invite member</h2>
          <label className="mb-2 block text-xs">
            <span className="mb-1 block text-muted">Email</span>
            <input
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
            />
          </label>
          <label className="mb-3 block text-xs">
            <span className="mb-1 block text-muted">Role</span>
            <select
              value={role}
              onChange={(e) => setRole(e.target.value)}
              className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
            >
              {["VIEWER", "OPERATOR", "FACILITY_MANAGER", "ADMINISTRATOR"].map((r) => (
                <option key={r} value={r}>
                  {r}
                </option>
              ))}
            </select>
          </label>
          <button
            type="button"
            className="rounded-md border border-live/40 bg-live/10 px-3 py-1.5 text-xs text-live"
            onClick={() => invite.mutate()}
          >
            Send invite
          </button>
          {inviteToken ? (
            <p className="mt-3 break-all font-mono text-[11px] text-muted">
              Invite token: {inviteToken}
            </p>
          ) : null}
        </Panel>
      </div>

      <Panel className="mt-4 p-4">
        <h2 className="mb-2 text-sm font-semibold">Compliance export</h2>
        <p className="mb-3 text-xs text-muted">
          Download immutable org-scoped audit events (plans, writes, invites, certification).
        </p>
        <button
          type="button"
          className="rounded-md border border-border px-3 py-1.5 text-xs"
          onClick={() => exportAudit.mutate()}
        >
          Export audit JSON
        </button>
      </Panel>
      {message ? <p className="mt-4 text-sm text-muted">{message}</p> : null}
    </div>
  );
}
