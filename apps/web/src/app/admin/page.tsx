"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { KeyRound, Settings2, Shield, Tag, Users } from "lucide-react";

import { useToast } from "@/components/notifications";
import { authApi, catalogApi } from "@/lib/api";
import { isAdmin, readStoredUser, type AuthUser } from "@/lib/auth";
import type { CatalogCategory, CatalogOptions, TicketLabel } from "@/types";

type EditableUser = {
  username: string;
  role: string;
  display_name: string;
  password: string;
};

const roleOptions = ["admin", "agent", "viewer"];

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
      <div className="ops-shell min-h-[100dvh] px-4 py-5 text-white sm:px-6 lg:px-8">
        <div className="mx-auto max-w-4xl rounded-[2rem] border border-rose-500/20 bg-black/20 p-8">
          <div className="mono-data text-[11px] uppercase tracking-[0.28em] text-rose-300">Admin access required</div>
          <h1 className="mt-3 text-3xl font-semibold text-white">This console is restricted to administrators</h1>
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
      </div>
    );
  }

  return (
    <div className="ops-shell min-h-[100dvh] px-4 py-5 text-white sm:px-6 lg:px-8">
      <div className="mx-auto max-w-7xl space-y-6">
        <div className="ops-glass rounded-[2rem] px-5 py-5 sm:px-7">
          <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
            <div>
              <div className="mono-data text-[11px] uppercase tracking-[0.28em] text-amber-300">Admin Console</div>
              <h1 className="mt-3 text-3xl font-semibold tracking-tight text-white">Users, permissions, categories, and labels</h1>
              <p className="mt-3 max-w-3xl text-sm leading-7 text-zinc-400">
                This keeps the operational control plane inside the new Aether design while restoring the management features a real ticketing system needs.
              </p>
            </div>
            <div className="flex flex-wrap gap-3">
              <Link
                href="/tickets/new"
                className="rounded-full bg-amber-500 px-4 py-2.5 text-sm font-semibold text-black transition hover:bg-amber-400"
              >
                New ticket
              </Link>
              <Link
                href="/command-center"
                className="rounded-full border border-zinc-700 bg-zinc-950/60 px-4 py-2.5 text-sm font-medium text-zinc-200 transition hover:border-zinc-500"
              >
                Back to command center
              </Link>
            </div>
          </div>
        </div>

        {isLoading ? (
          <div className="rounded-[1.5rem] border border-zinc-800 bg-black/20 p-6 text-sm text-zinc-400">
            Loading admin data...
          </div>
        ) : null}

        <div className="grid gap-6 xl:grid-cols-2">
          <section className="ops-card rounded-[1.75rem] p-6">
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
                <div key={entry.username} className="rounded-[1.25rem] border border-zinc-800 bg-zinc-950/60 p-4">
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
            <div className="ops-card rounded-[1.75rem] p-6">
              <div className="flex items-center gap-3">
                <Settings2 className="h-5 w-5 text-amber-300" />
                <div>
                  <div className="text-lg font-semibold text-white">Category management</div>
                  <div className="mt-1 text-sm text-zinc-500">Control ticket taxonomy without leaving the product.</div>
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
                  <div key={category.id} className="rounded-[1.25rem] border border-zinc-800 bg-zinc-950/60 p-4">
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

            <div className="ops-card rounded-[1.75rem] p-6">
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

            <div className="ops-card rounded-[1.75rem] p-6">
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

            <div className="ops-card rounded-[1.75rem] p-6">
              <div className="flex items-center gap-3">
                <KeyRound className="h-5 w-5 text-amber-300" />
                <div>
                  <div className="text-lg font-semibold text-white">Change your password</div>
                  <div className="mt-1 text-sm text-zinc-500">Keep your own account secure without leaving the console.</div>
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
      </div>
    </div>
  );
}
