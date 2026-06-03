"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { KeyRound, Plus, Settings2, Shield, Tag, Users } from "lucide-react";

import { OpsShell } from "@/components/ops-shell";
import { useToast } from "@/components/notifications";
import { authApi, catalogApi, governanceApi, intelligenceApi } from "@/lib/api";
import { isAdmin, readStoredUser, type AuthUser } from "@/lib/auth";
import type {
  CatalogCategory,
  CatalogOptions,
  GovernanceSummaryResponse,
  IntelligenceHealthResponse,
  TicketLabel,
} from "@/types";

type EditableUser = {
  username: string;
  role: string;
  display_name: string;
  password: string;
};

const roleOptions = ["admin", "agent", "viewer"];

function formatNumber(value: unknown, digits = 0) {
  const numberValue = Number(value ?? 0);
  return Number.isFinite(numberValue) ? numberValue.toFixed(digits) : (0).toFixed(digits);
}

export default function AdminPage() {
  const toast = useToast();
  const [user, setUser] = useState<AuthUser | null>(null);
  const [options, setOptions] = useState<CatalogOptions | null>(null);
  const [users, setUsers] = useState<EditableUser[]>([]);
  const [newUser, setNewUser] = useState({
    username: "",
    display_name: "",
    password: "",
    role: "viewer",
  });
  const [newCategory, setNewCategory] = useState({ name: "", color: "#6366f1", icon: "fa-tag" });
  const [newLabel, setNewLabel] = useState({ name: "", color: "#3b82f6" });
  const [newAssignee, setNewAssignee] = useState("");
  const [passwordForm, setPasswordForm] = useState({
    current_password: "",
    new_password: "",
    confirm_password: "",
  });
  const [isLoading, setIsLoading] = useState(true);
  const [governance, setGovernance] = useState<GovernanceSummaryResponse | null>(null);
  const [governanceError, setGovernanceError] = useState<string | null>(null);
  const [intelligenceHealth, setIntelligenceHealth] = useState<IntelligenceHealthResponse | null>(null);

  const categories = useMemo<CatalogCategory[]>(() => options?.categories ?? [], [options]);
  const labels = useMemo<TicketLabel[]>(() => options?.labels ?? [], [options]);
  const assignees = useMemo<string[]>(() => options?.assignees ?? [], [options]);
  const adminAccess = isAdmin(user);

  useEffect(() => {
    setUser(readStoredUser());
  }, []);

  const loadConsole = useCallback(async () => {
    setIsLoading(true);
    try {
      const [usersResponse, optionsResponse] = await Promise.all([
        authApi.listUsers(),
        catalogApi.options(),
      ]);
      const loadedUsers = (usersResponse.data as Array<{ username: string; role: string; display_name: string }>).map(
        (entry) => ({
          ...entry,
          password: "",
        }),
      );
      setUsers(loadedUsers);
      setOptions(optionsResponse.data as CatalogOptions);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unable to load the admin console.";
      toast.error("Admin console unavailable", message);
    } finally {
      setIsLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    if (adminAccess) {
      void loadConsole();
    } else {
      setIsLoading(false);
    }
  }, [adminAccess, loadConsole]);

  useEffect(() => {
    if (!adminAccess) {
      setGovernance(null);
      setIntelligenceHealth(null);
      return;
    }
    let cancelled = false;
    governanceApi
      .summary()
      .then((response) => {
        if (cancelled) {
          return;
        }
        setGovernance(response.data as GovernanceSummaryResponse);
        setGovernanceError(null);
      })
      .catch((error: unknown) => {
        if (cancelled) {
          return;
        }
        const message = error instanceof Error ? error.message : "Governance summary unavailable";
        setGovernanceError(message);
      });
    intelligenceApi
      .health()
      .then((response) => {
        if (!cancelled) {
          setIntelligenceHealth(response.data as IntelligenceHealthResponse);
        }
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [adminAccess]);

  const updateUserDraft = (username: string, patch: Partial<EditableUser>) => {
    setUsers((current) =>
      current.map((entry) => (entry.username === username ? { ...entry, ...patch } : entry)),
    );
  };

  const handleCreateUser = async () => {
    if (!newUser.username.trim() || !newUser.password) {
      toast.error("Missing user details", "Username and password are required.");
      return;
    }
    try {
      await authApi.createUser({
        username: newUser.username.trim(),
        display_name: newUser.display_name.trim() || newUser.username.trim(),
        password: newUser.password,
        role: newUser.role,
      });
      setNewUser({ username: "", display_name: "", password: "", role: "viewer" });
      toast.success("User created", newUser.username.trim());
      await loadConsole();
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unable to create the user.";
      toast.error("Create failed", message);
    }
  };

  const handleSaveUser = async (entry: EditableUser) => {
    try {
      await authApi.updateUser(entry.username, {
        role: entry.role,
        display_name: entry.display_name,
        password: entry.password || undefined,
      });
      toast.success("User updated", entry.username);
      await loadConsole();
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unable to update the user.";
      toast.error("Update failed", message);
    }
  };

  const handleDeleteUser = async (username: string) => {
    if (!window.confirm(`Delete user ${username}?`)) {
      return;
    }
    try {
      await authApi.deleteUser(username);
      toast.success("User deleted", username);
      await loadConsole();
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unable to delete the user.";
      toast.error("Delete failed", message);
    }
  };

  const handleCreateCategory = async () => {
    if (!newCategory.name.trim()) {
      toast.error("Missing category name", "A category name is required.");
      return;
    }
    try {
      await catalogApi.createCategory({
        name: newCategory.name.trim(),
        color: newCategory.color,
        icon: newCategory.icon.trim() || "fa-tag",
      });
      setNewCategory({ name: "", color: "#6366f1", icon: "fa-tag" });
      toast.success("Category created", "The category is ready for ticket assignment.");
      await loadConsole();
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unable to create the category.";
      toast.error("Create failed", message);
    }
  };

  const handleUpdateCategory = async (category: CatalogCategory, patch: Partial<CatalogCategory>) => {
    try {
      await catalogApi.updateCategory(category.id, patch);
      toast.success("Category updated", category.name);
      await loadConsole();
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unable to update the category.";
      toast.error("Update failed", message);
    }
  };

  const handleDeleteCategory = async (categoryId: number) => {
    if (!window.confirm("Delete this category? Tickets keeping it will fall back to the category name as request type.")) {
      return;
    }
    try {
      await catalogApi.deleteCategory(categoryId);
      toast.success("Category deleted", "Existing tickets kept their current meaning.");
      await loadConsole();
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unable to delete the category.";
      toast.error("Delete failed", message);
    }
  };

  const handleCreateLabel = async () => {
    if (!newLabel.name.trim()) {
      toast.error("Missing label name", "A label name is required.");
      return;
    }
    try {
      await catalogApi.createLabel({
        name: newLabel.name.trim(),
        color: newLabel.color,
      });
      setNewLabel({ name: "", color: "#3b82f6" });
      toast.success("Label created", newLabel.name.trim().toUpperCase());
      await loadConsole();
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unable to create the label.";
      toast.error("Create failed", message);
    }
  };

  const handleDeleteLabel = async (labelId: number) => {
    if (!window.confirm("Delete this label?")) {
      return;
    }
    try {
      await catalogApi.deleteLabel(labelId);
      toast.success("Label deleted", "It was removed from the label set.");
      await loadConsole();
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unable to delete the label.";
      toast.error("Delete failed", message);
    }
  };

  const handleCreateAssignee = async () => {
    if (!newAssignee.trim()) {
      toast.error("Missing assignee name", "An assignee name is required.");
      return;
    }
    try {
      await catalogApi.createAssignee(newAssignee.trim());
      setNewAssignee("");
      toast.success("Assignee created", "The assignee is ready for ticket assignment.");
      await loadConsole();
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unable to create the assignee.";
      toast.error("Create failed", message);
    }
  };

  const handleDeleteAssignee = async (displayName: string) => {
    if (!window.confirm(`Delete assignee ${displayName}?`)) {
      return;
    }
    try {
      await catalogApi.deleteAssignee(displayName);
      toast.success("Assignee deleted", displayName);
      await loadConsole();
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unable to delete the assignee.";
      toast.error("Delete failed", message);
    }
  };

  const handleChangePassword = async () => {
    if (!passwordForm.new_password || passwordForm.new_password !== passwordForm.confirm_password) {
      toast.error("Password mismatch", "Make sure the new password and confirmation match.");
      return;
    }
    try {
      await authApi.changePassword(passwordForm.current_password, passwordForm.new_password);
      setPasswordForm({ current_password: "", new_password: "", confirm_password: "" });
      toast.success("Password updated", "Your credentials have been changed.");
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unable to change the password.";
      toast.error("Password change failed", message);
    }
  };

  if (!adminAccess) {
    return (
      <OpsShell
        eyebrow="Aether OpsCenter"
        title="Administration"
        subtitle="Users, roles, categories, labels, assignees, and credential maintenance."
        statusPill={{ kind: "error", label: "Restricted" }}
        showNotificationBell
      >
        <div className="mx-auto max-w-4xl rounded-[2rem] border border-rose-500/20 bg-black/20 p-8">
          <h1 className="text-3xl font-semibold text-white">This console is restricted to administrators</h1>
          <p className="mt-4 text-sm leading-7 text-zinc-400">
            Your current role does not allow user, category, or label administration.
          </p>
          <div className="mt-6 flex gap-3">
            <Link
              href="/command-center"
              className="rounded-full border border-zinc-700 bg-zinc-950/60 px-4 py-2.5 text-sm font-medium text-zinc-200 transition hover:border-zinc-500"
            >
              Return to command center
            </Link>
          </div>
        </div>
      </OpsShell>
    );
  }

  return (
    <OpsShell
      eyebrow="Aether OpsCenter"
      title="Administration"
      subtitle="Users, roles, categories, labels, assignees, and credential maintenance."
      statusPill={{ kind: "ready", label: "Live" }}
      headerActions={
        <Link
          href="/tickets/new"
          className="inline-flex items-center gap-2 rounded-2xl bg-amber-500 px-4 py-2.5 text-sm font-semibold text-black transition hover:bg-amber-400"
        >
          <Plus className="h-4 w-4" />
          New ticket
        </Link>
      }
      showNotificationBell
    >
      <div className="mx-auto max-w-7xl space-y-6">
        {isLoading ? (
          <div className="rounded-[22px] border border-zinc-800 bg-black/20 p-6 text-sm text-zinc-400">
            Loading admin data...
          </div>
        ) : null}

        <div className="grid gap-6 xl:grid-cols-2">
          <section className="ops-card rounded-[22px] p-6">
            <div className="flex items-center gap-3">
              <Users className="h-5 w-5 text-amber-300" />
              <div>
                <div className="text-lg font-semibold text-white">User management</div>
                <div className="mt-1 text-sm text-zinc-500">Create accounts, assign privileges, and reset credentials.</div>
              </div>
            </div>

            <div className="mt-6 grid gap-3 md:grid-cols-2">
              <input
                value={newUser.username}
                onChange={(event) => setNewUser((current) => ({ ...current, username: event.target.value }))}
                className="rounded-2xl border border-zinc-700 bg-zinc-950/70 px-4 py-3 text-sm text-white"
                placeholder="Username"
              />
              <input
                value={newUser.display_name}
                onChange={(event) => setNewUser((current) => ({ ...current, display_name: event.target.value }))}
                className="rounded-2xl border border-zinc-700 bg-zinc-950/70 px-4 py-3 text-sm text-white"
                placeholder="Display name"
              />
              <input
                value={newUser.password}
                onChange={(event) => setNewUser((current) => ({ ...current, password: event.target.value }))}
                type="password"
                className="rounded-2xl border border-zinc-700 bg-zinc-950/70 px-4 py-3 text-sm text-white"
                placeholder="Temporary password"
              />
              <select
                value={newUser.role}
                onChange={(event) => setNewUser((current) => ({ ...current, role: event.target.value }))}
                className="rounded-2xl border border-zinc-700 bg-zinc-950/70 px-4 py-3 text-sm text-white"
              >
                {roleOptions.map((role) => (
                  <option key={role} value={role}>
                    {role}
                  </option>
                ))}
              </select>
            </div>
            <button
              type="button"
              onClick={handleCreateUser}
              className="mt-4 rounded-full bg-amber-500 px-4 py-2.5 text-sm font-semibold text-black transition hover:bg-amber-400"
            >
              Create user
            </button>

            <div className="mt-6 space-y-3">
              {users.map((entry) => (
                <div key={entry.username} className="rounded-2xl border border-zinc-800 bg-zinc-950/60 p-4">
                  <div className="grid gap-3 md:grid-cols-2">
                    <input
                      value={entry.display_name}
                      onChange={(event) => updateUserDraft(entry.username, { display_name: event.target.value })}
                      className="rounded-2xl border border-zinc-700 bg-black/30 px-4 py-3 text-sm text-white"
                    />
                    <select
                      value={entry.role}
                      onChange={(event) => updateUserDraft(entry.username, { role: event.target.value })}
                      className="rounded-2xl border border-zinc-700 bg-black/30 px-4 py-3 text-sm text-white"
                    >
                      {roleOptions.map((role) => (
                        <option key={role} value={role}>
                          {role}
                        </option>
                      ))}
                    </select>
                    <input
                      value={entry.password}
                      onChange={(event) => updateUserDraft(entry.username, { password: event.target.value })}
                      type="password"
                      className="rounded-2xl border border-zinc-700 bg-black/30 px-4 py-3 text-sm text-white md:col-span-2"
                      placeholder="Optional new password"
                    />
                  </div>
                  <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
                    <div className="mono-data text-xs text-zinc-500">{entry.username}</div>
                    <div className="flex gap-2">
                      <button
                        type="button"
                        onClick={() => handleSaveUser(entry)}
                        className="rounded-full border border-zinc-700 bg-black/30 px-3 py-2 text-xs font-medium text-zinc-200 transition hover:border-zinc-500"
                      >
                        Save
                      </button>
                      {entry.username !== "admin" ? (
                        <button
                          type="button"
                          onClick={() => handleDeleteUser(entry.username)}
                          className="rounded-full border border-rose-400/20 bg-rose-500/10 px-3 py-2 text-xs font-medium text-rose-100 transition hover:bg-rose-500/20"
                        >
                          Delete
                        </button>
                      ) : null}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </section>

          <section className="space-y-6">
            <div className="ops-card rounded-[22px] p-6">
              <div className="flex items-center gap-3">
                <Settings2 className="h-5 w-5 text-amber-300" />
                <div>
                  <div className="text-lg font-semibold text-white">Category management</div>
                  <div className="mt-1 text-sm text-zinc-500">Add, edit, and disable ticket categories.</div>
                </div>
              </div>

              <div className="mt-6 grid gap-3 md:grid-cols-[1fr,160px,160px]">
                <input
                  value={newCategory.name}
                  onChange={(event) => setNewCategory((current) => ({ ...current, name: event.target.value }))}
                  className="rounded-2xl border border-zinc-700 bg-zinc-950/70 px-4 py-3 text-sm text-white"
                  placeholder="Category name"
                />
                <input
                  value={newCategory.color}
                  onChange={(event) => setNewCategory((current) => ({ ...current, color: event.target.value }))}
                  className="rounded-2xl border border-zinc-700 bg-zinc-950/70 px-4 py-3 text-sm text-white"
                  placeholder="#6366f1"
                />
                <input
                  value={newCategory.icon}
                  onChange={(event) => setNewCategory((current) => ({ ...current, icon: event.target.value }))}
                  className="rounded-2xl border border-zinc-700 bg-zinc-950/70 px-4 py-3 text-sm text-white"
                  placeholder="fa-tag"
                />
              </div>
              <button
                type="button"
                onClick={handleCreateCategory}
                className="mt-4 rounded-full bg-amber-500 px-4 py-2.5 text-sm font-semibold text-black transition hover:bg-amber-400"
              >
                Create category
              </button>

              <div className="mt-6 space-y-3">
                {categories.map((category) => (
                  <div key={category.id} className="rounded-2xl border border-zinc-800 bg-zinc-950/60 p-4">
                    <div className="flex items-center justify-between gap-3">
                      <div className="flex items-center gap-3">
                        <span
                          className="h-3 w-3 rounded-full"
                          style={{ backgroundColor: category.color }}
                        />
                        <div>
                          <div className="text-sm font-semibold text-white">{category.name}</div>
                          <div className="mt-1 text-xs text-zinc-500">{category.icon}</div>
                        </div>
                      </div>
                      <div className="flex gap-2">
                        <button
                          type="button"
                          onClick={() => handleUpdateCategory(category, { is_active: !category.is_active })}
                          className="rounded-full border border-zinc-700 bg-black/30 px-3 py-2 text-xs font-medium text-zinc-200 transition hover:border-zinc-500"
                        >
                          {category.is_active ? "Disable" : "Enable"}
                        </button>
                        <button
                          type="button"
                          onClick={() => handleDeleteCategory(category.id)}
                          className="rounded-full border border-rose-400/20 bg-rose-500/10 px-3 py-2 text-xs font-medium text-rose-100 transition hover:bg-rose-500/20"
                        >
                          Delete
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="ops-card rounded-[22px] p-6">
              <div className="flex items-center gap-3">
                <Users className="h-5 w-5 text-amber-300" />
                <div>
                  <div className="text-lg font-semibold text-white">Assignee roster</div>
                  <div className="mt-1 text-sm text-zinc-500">Add or remove the operator names available in ticket assignment.</div>
                </div>
              </div>

              <div className="mt-6 flex flex-wrap gap-3">
                <input
                  value={newAssignee}
                  onChange={(event) => setNewAssignee(event.target.value)}
                  className="min-w-[220px] flex-1 rounded-2xl border border-zinc-700 bg-zinc-950/70 px-4 py-3 text-sm text-white"
                  placeholder="Assignee display name"
                />
                <button
                  type="button"
                  onClick={handleCreateAssignee}
                  className="rounded-full bg-amber-500 px-4 py-2.5 text-sm font-semibold text-black transition hover:bg-amber-400"
                >
                  Create assignee
                </button>
              </div>

              <div className="mt-6 flex flex-wrap gap-2">
                {assignees.map((assignee) => (
                  <div key={assignee} className="inline-flex items-center gap-2 rounded-full border border-zinc-700 bg-zinc-950/60 px-3 py-2">
                    <span className="text-xs font-medium text-zinc-200">{assignee}</span>
                    <button
                      type="button"
                      onClick={() => handleDeleteAssignee(assignee)}
                      className="rounded-full border border-rose-400/20 bg-rose-500/10 px-2 py-1 text-[11px] text-rose-100 transition hover:bg-rose-500/20"
                    >
                      Delete
                    </button>
                  </div>
                ))}
              </div>
            </div>

            <div className="ops-card rounded-[22px] p-6">
              <div className="flex items-center gap-3">
                <Tag className="h-5 w-5 text-amber-300" />
                <div>
                  <div className="text-lg font-semibold text-white">Labels</div>
                  <div className="mt-1 text-sm text-zinc-500">Create and remove colored ticket tags.</div>
                </div>
              </div>

              <div className="mt-6 grid gap-3 md:grid-cols-[1fr,180px]">
                <input
                  value={newLabel.name}
                  onChange={(event) => setNewLabel((current) => ({ ...current, name: event.target.value }))}
                  className="rounded-2xl border border-zinc-700 bg-zinc-950/70 px-4 py-3 text-sm text-white"
                  placeholder="Label name"
                />
                <input
                  value={newLabel.color}
                  onChange={(event) => setNewLabel((current) => ({ ...current, color: event.target.value }))}
                  className="rounded-2xl border border-zinc-700 bg-zinc-950/70 px-4 py-3 text-sm text-white"
                  placeholder="#3b82f6"
                />
              </div>
              <button
                type="button"
                onClick={handleCreateLabel}
                className="mt-4 rounded-full bg-amber-500 px-4 py-2.5 text-sm font-semibold text-black transition hover:bg-amber-400"
              >
                Create label
              </button>

              <div className="mt-6 flex flex-wrap gap-2">
                {labels.map((label) => (
                  <div key={label.id} className="inline-flex items-center gap-2 rounded-full border border-zinc-700 bg-zinc-950/60 px-3 py-2">
                    <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: label.color }} />
                    <span className="text-xs font-medium text-zinc-200">{label.name}</span>
                    <button
                      type="button"
                      onClick={() => handleDeleteLabel(label.id)}
                      className="rounded-full border border-rose-400/20 bg-rose-500/10 px-2 py-1 text-[11px] text-rose-100 transition hover:bg-rose-500/20"
                    >
                      Delete
                    </button>
                  </div>
                ))}
              </div>
            </div>

            <div className="ops-card rounded-[22px] p-6">
              <div className="flex items-center gap-3">
                <KeyRound className="h-5 w-5 text-amber-300" />
                <div>
                  <div className="text-lg font-semibold text-white">Change your password</div>
                  <div className="mt-1 text-sm text-zinc-500">Change your account password.</div>
                </div>
              </div>

              <div className="mt-6 grid gap-3">
                <input
                  type="password"
                  value={passwordForm.current_password}
                  onChange={(event) => setPasswordForm((current) => ({ ...current, current_password: event.target.value }))}
                  className="rounded-2xl border border-zinc-700 bg-zinc-950/70 px-4 py-3 text-sm text-white"
                  placeholder="Current password"
                />
                <input
                  type="password"
                  value={passwordForm.new_password}
                  onChange={(event) => setPasswordForm((current) => ({ ...current, new_password: event.target.value }))}
                  className="rounded-2xl border border-zinc-700 bg-zinc-950/70 px-4 py-3 text-sm text-white"
                  placeholder="New password"
                />
                <input
                  type="password"
                  value={passwordForm.confirm_password}
                  onChange={(event) => setPasswordForm((current) => ({ ...current, confirm_password: event.target.value }))}
                  className="rounded-2xl border border-zinc-700 bg-zinc-950/70 px-4 py-3 text-sm text-white"
                  placeholder="Confirm new password"
                />
              </div>
              <button
                type="button"
                onClick={handleChangePassword}
                className="mt-4 rounded-full bg-amber-500 px-4 py-2.5 text-sm font-semibold text-black transition hover:bg-amber-400"
              >
                Update password
              </button>
            </div>
          </section>
        </div>

        <section className="ops-card rounded-[22px] p-6">
          <div className="flex items-center gap-3">
            <Shield className="h-5 w-5 text-amber-300" />
            <div>
              <div className="text-lg font-semibold text-white">Decision engine governance</div>
              <div className="mt-1 text-sm text-zinc-500">
                Decision engine drift status, graph health, and engine metadata.
              </div>
            </div>
          </div>
          {governanceError ? (
            <div className="mt-6 rounded-2xl border border-rose-500/20 bg-rose-500/5 p-4 text-sm text-rose-100">
              Governance summary unavailable: {governanceError}
            </div>
          ) : null}
          {governance ? (
            <div className="mt-6 grid gap-4 lg:grid-cols-3">
              <div className="rounded-2xl border border-zinc-800/60 bg-black/20 p-4">
                <div className="text-sm font-medium text-zinc-300">
                  Drift status
                </div>
                <div
                  className={`mt-3 text-2xl font-semibold ${
                    governance.drift.status === "drift"
                      ? "text-rose-200"
                      : governance.drift.status === "watch"
                        ? "text-amber-200"
                        : "text-emerald-200"
                  }`}
                >
                  {governance.drift.status.toUpperCase()}
                </div>
                <div className="mt-2 text-xs text-zinc-400">
                  Decisions {governance.drift.current_decision_count ?? 0} (vs prior{" "}
                  {governance.drift.prior_decision_count ?? 0})
                </div>
                {governance.drift.priority_shift ? (
                  <div className="mt-1 text-xs text-zinc-400">
                    Priority Δ {formatNumber(governance.drift.priority_shift.delta, 2)} ·{" "}
                    {formatNumber(governance.drift.priority_shift.pct_change, 1)}%
                  </div>
                ) : null}
                {governance.drift.root_cause_spikes?.length ? (
                  <div className="mt-3 space-y-1 text-xs text-zinc-300">
                    {governance.drift.root_cause_spikes.slice(0, 3).map((spike) => (
                      <div key={spike.root_cause}>
                        <span className="text-amber-200">{spike.root_cause}</span>{" "}
                        {formatNumber(spike.pct_change, 0)}%
                      </div>
                    ))}
                  </div>
                ) : null}
              </div>
              <div className="rounded-2xl border border-zinc-800/60 bg-black/20 p-4">
                <div className="text-sm font-medium text-zinc-300">
                  Graph health
                </div>
                <div className="mt-3 text-2xl font-semibold text-zinc-50">
                  {governance.graph.node_count} nodes · {governance.graph.edge_count} edges
                </div>
                <div className="mt-2 text-xs text-zinc-400">
                  avg degree {formatNumber(governance.graph.average_degree, 2)} · isolated{" "}
                  {governance.graph.isolated_count}
                </div>
                {Object.keys(governance.graph.edges_by_type ?? {}).length ? (
                  <div className="mt-3 space-y-1 text-xs text-zinc-300">
                    {Object.entries(governance.graph.edges_by_type ?? {}).map(([edgeType, count]) => (
                      <div key={edgeType} className="flex items-center justify-between">
                        <span className="text-zinc-400">{edgeType}</span>
                        <span className="font-mono">{count}</span>
                      </div>
                    ))}
                  </div>
                ) : null}
              </div>
              <div className="rounded-2xl border border-zinc-800/60 bg-black/20 p-4">
                <div className="text-sm font-medium text-zinc-300">
                  Engine card
                </div>
                <div className="mt-3 text-base font-semibold text-zinc-50">
                  {governance.card.engine.name}
                </div>
                <div className="mt-1 text-xs text-zinc-400">
                  {governance.card.engine.kind} · schema {governance.card.engine.decision_schema_version}
                </div>
                <ul className="mt-3 space-y-1 text-xs text-zinc-300">
                  {governance.card.what_this_engine_is.slice(0, 3).map((line) => (
                    <li key={line}>• {line}</li>
                  ))}
                </ul>
                {governance.card.guardrails?.length ? (
                  <div className="mt-3 space-y-1 text-xs text-zinc-400">
                    {governance.card.guardrails.slice(0, 3).map((guard) => (
                      <div key={guard}>• {guard}</div>
                    ))}
                  </div>
                ) : null}
                {governance.card.ownership ? (
                  <div className="mt-3 text-xs text-zinc-400">
                    {governance.card.ownership.team} · review {governance.card.ownership.review_cadence}
                  </div>
                ) : null}
              </div>
            </div>
           ) : null}
           {intelligenceHealth ? (
            <div className="mt-6 grid gap-4 lg:grid-cols-2">
              <div className="rounded-2xl border border-zinc-800/60 bg-black/20 p-4">
                <div className="text-sm font-medium text-zinc-300">
                  Engine health
                </div>
                <div className="mt-3 text-2xl font-semibold text-emerald-200">
                  {intelligenceHealth.status.toUpperCase()}
                </div>
                <div className="mt-2 text-xs text-zinc-400">
                  {intelligenceHealth.engine.name} · {intelligenceHealth.engine.version}
                </div>
                <div className="mt-1 text-xs text-zinc-400">
                  Decision records: {intelligenceHealth.subsystems?.decision_records?.count ?? 0}
                  {" · "}Recommendations: {intelligenceHealth.subsystems?.recommendations?.count ?? 0}
                  {" · "}Feedback: {intelligenceHealth.subsystems?.operator_feedback?.count ?? 0}
                </div>
              </div>
              <div className="rounded-2xl border border-zinc-800/60 bg-black/20 p-4">
                <div className="text-sm font-medium text-zinc-300">
                  Feedback loop
                </div>
                <div className="mt-3 text-sm text-zinc-200">
                  {intelligenceHealth.feedback_loop.enabled ? "Active" : "Disabled"}
                  {" · "}cap {intelligenceHealth.feedback_loop.adjustment_cap}
                  {" · "}decay {intelligenceHealth.feedback_loop.decay_factor}
                </div>
                {intelligenceHealth.truthful_disclosure ? (
                  <ul className="mt-3 space-y-1 text-xs text-zinc-400">
                    {intelligenceHealth.truthful_disclosure.no_external_llm ? <li>No external LLM</li> : null}
                    {intelligenceHealth.truthful_disclosure.no_trained_ml_model ? <li>No trained ML model</li> : null}
                    {intelligenceHealth.truthful_disclosure.actions_are_real_workflow_mutations ? <li>Actions are real mutations</li> : null}
                  </ul>
                ) : null}
              </div>
            </div>
           ) : null}
         </section>

        {/* Phase 8 quick links (portal, KB, realtime note) */}
        <section className="ops-card rounded-[22px] p-6 mt-4">
          <div className="text-lg font-semibold">Phase 8 parity (portal / KB / realtime / email)</div>
          <div className="mt-2 text-sm text-zinc-400">Portal submit/status: <a className="underline" href="/portal">/portal</a>. KB admin/search wired. WS at /ws/{'{topic}'}. Email via SMTP_* config (see .env.example). Full builder/RBAC/SLA in follow-ups.</div>
        </section>
      </div>
    </OpsShell>
  );
}
