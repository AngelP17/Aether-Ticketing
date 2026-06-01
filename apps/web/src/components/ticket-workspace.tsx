"use client";

import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  FileText,
  MessageSquare,
  Paperclip,
  Plus,
  Save,
  Shield,
  Trash2,
} from "lucide-react";

import { FileDropzone } from "@/components/file-dropzone";
import { useToast } from "@/components/notifications";
import { authApi, catalogApi, ticketsApi } from "@/lib/api";
import { canWriteTickets, isAdmin, readStoredUser, type AuthUser } from "@/lib/auth";
import type {
  CatalogOptions,
  TicketAttachment,
  TicketComment,
  TicketDetailPayload,
  TicketLabel,
} from "@/types";

type TicketWorkspaceProps = {
  ticketId?: string;
};

type TicketFormState = {
  title: string;
  status: string;
  priority: string;
  category_id: string;
  request_type: string;
  staff_assigned: string;
  requester: string;
  description: string;
  resolution_notes: string;
  site_id: string;
  label_ids: number[];
};

const defaultFormState: TicketFormState = {
  title: "",
  status: "Open",
  priority: "Low",
  category_id: "",
  request_type: "",
  staff_assigned: "",
  requester: "",
  description: "",
  resolution_notes: "",
  site_id: "",
  label_ids: [],
};

const statuses = ["Open", "In Progress", "Waiting for Info", "Resolved", "Closed"];
const priorities = ["Low", "Medium", "High", "Critical"];
const roleLabels: Record<string, string> = {
  admin: "Admin",
  agent: "Agent",
  viewer: "Viewer",
};

function formatRelativeDate(value?: string) {
  if (!value) {
    return "Unknown";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString();
}

function formatFileSize(size: number) {
  if (size >= 1024 * 1024) {
    return `${(size / (1024 * 1024)).toFixed(1)} MB`;
  }
  return `${Math.max(1, Math.round(size / 1024))} KB`;
}

function isImageAttachment(attachment: TicketAttachment) {
  return attachment.mime_type.startsWith("image/");
}

function attachmentLink(attachment: TicketAttachment) {
  return attachment.url;
}

export function TicketWorkspace({ ticketId }: TicketWorkspaceProps) {
  const router = useRouter();
  const toast = useToast();
  const [user, setUser] = useState<AuthUser | null>(null);
  const [options, setOptions] = useState<CatalogOptions | null>(null);
  const [detail, setDetail] = useState<TicketDetailPayload | null>(null);
  const [form, setForm] = useState<TicketFormState>(defaultFormState);
  const [ticketFiles, setTicketFiles] = useState<File[]>([]);
  const [commentFiles, setCommentFiles] = useState<File[]>([]);
  const [commentBody, setCommentBody] = useState("");
  const [editingCommentId, setEditingCommentId] = useState<number | null>(null);
  const [editingCommentBody, setEditingCommentBody] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [isSubmittingComment, setIsSubmittingComment] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [quickCategoryName, setQuickCategoryName] = useState("");
  const [quickAssigneeName, setQuickAssigneeName] = useState("");

  const writable = canWriteTickets(user);
  const admin = isAdmin(user);

  const currentLabels = useMemo<TicketLabel[]>(() => options?.labels ?? [], [options]);
  const currentAssignees = useMemo(() => {
    const names = new Set(options?.assignees ?? []);
    if (form.staff_assigned.trim()) {
      names.add(form.staff_assigned.trim());
    }
    return Array.from(names).sort((left, right) => left.localeCompare(right));
  }, [form.staff_assigned, options?.assignees]);

  useEffect(() => {
    setUser(readStoredUser());
  }, []);

  const loadOptions = async () => {
    const optionsResponse = await catalogApi.options();
    const loadedOptions = optionsResponse.data as CatalogOptions;
    setOptions(loadedOptions);
    return loadedOptions;
  };

  useEffect(() => {
    let active = true;

    const load = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const [loadedOptions, detailResponse] = await Promise.all([
          loadOptions(),
          ticketId ? ticketsApi.get(ticketId) : Promise.resolve(null),
        ]);

        if (!active) {
          return;
        }

        if (detailResponse) {
          const loadedDetail = detailResponse.data as TicketDetailPayload;
          setDetail(loadedDetail);
          setForm({
            title: loadedDetail.ticket.title || "",
            status: loadedDetail.ticket.status || "Open",
            priority: loadedDetail.ticket.priority_raw || "Low",
            category_id: loadedDetail.ticket.category_id ? String(loadedDetail.ticket.category_id) : "",
            request_type: loadedDetail.ticket.request_type || "",
            staff_assigned: loadedDetail.ticket.assignee || "",
            requester: loadedDetail.ticket.requester || "",
            description: loadedDetail.ticket.description || "",
            resolution_notes: loadedDetail.ticket.resolution_notes || "",
            site_id: loadedDetail.ticket.site || "",
            label_ids: loadedDetail.ticket.labels?.map((label) => label.id) || [],
          });
        } else {
          setDetail(null);
          setForm(defaultFormState);
        }
      } catch (loadError) {
        if (!active) {
          return;
        }
        setError(loadError instanceof Error ? loadError.message : "Unable to load the ticket workspace.");
      } finally {
        if (active) {
          setIsLoading(false);
        }
      }
    };

    void load();

    return () => {
      active = false;
    };
  }, [ticketId]);

  const refreshDetail = async () => {
    if (!ticketId) {
      return;
    }
    const response = await ticketsApi.get(ticketId);
    setDetail(response.data as TicketDetailPayload);
  };

  const refreshOptions = async () => {
    await loadOptions();
  };

  const uploadFiles = async (targetTicketId: string, files: File[], commentId?: number) => {
    for (const file of files) {
      const formData = new FormData();
      formData.append("file", file);
      await ticketsApi.uploadAttachment(targetTicketId, formData, commentId);
    }
  };

  const handleSaveTicket = async () => {
    if (!writable) {
      toast.error("Read-only account", "Your role does not allow ticket changes.");
      return;
    }

    if (!form.title.trim()) {
      toast.error("Missing title", "Every ticket needs a title.");
      return;
    }

    setIsSaving(true);
    try {
      const payload = {
        title: form.title.trim(),
        status: form.status,
        priority: form.priority,
        category_id: form.category_id ? Number(form.category_id) : null,
        request_type: form.request_type.trim() || null,
        staff_assigned: form.staff_assigned || null,
        requester: form.requester.trim() || null,
        description: form.description.trim() || null,
        resolution_notes: form.resolution_notes.trim() || null,
        site_id: form.site_id.trim() || null,
        label_ids: form.label_ids,
      };

      const response = ticketId
        ? await ticketsApi.update(ticketId, payload)
        : await ticketsApi.create(payload);
      const nextDetail = response.data as TicketDetailPayload;
      const nextTicketId = nextDetail.ticket.ticket_id;

      if (ticketFiles.length) {
        await uploadFiles(nextTicketId, ticketFiles);
        setTicketFiles([]);
      }

      setDetail(nextDetail);
      toast.success(ticketId ? "Ticket updated" : "Ticket created", nextTicketId);

      if (!ticketId) {
        router.replace(`/tickets/${nextTicketId}`);
        return;
      }

      await refreshDetail();
    } catch (saveError) {
      const message = saveError instanceof Error ? saveError.message : "Unable to save the ticket.";
      toast.error("Save failed", message);
    } finally {
      setIsSaving(false);
    }
  };

  const handleDeleteTicket = async () => {
    if (!ticketId || !writable) {
      return;
    }
    if (!window.confirm(`Delete ticket ${ticketId}?`)) {
      return;
    }

    try {
      await ticketsApi.delete(ticketId);
      toast.success("Ticket deleted", `${ticketId} was removed`);
      router.push("/command-center");
    } catch (deleteError) {
      const message = deleteError instanceof Error ? deleteError.message : "Unable to delete the ticket.";
      toast.error("Delete failed", message);
    }
  };

  const handleSubmitComment = async () => {
    if (!ticketId || !writable) {
      toast.error("Read-only account", "Your role does not allow comment changes.");
      return;
    }
    if (!commentBody.trim()) {
      toast.error("Missing comment", "Write a comment before submitting it.");
      return;
    }

    setIsSubmittingComment(true);
    try {
      const response = await ticketsApi.addComment(ticketId, commentBody.trim());
      const comment = response.data as TicketComment;
      if (commentFiles.length) {
        await uploadFiles(ticketId, commentFiles, comment.id);
        setCommentFiles([]);
      }
      setCommentBody("");
      await refreshDetail();
      toast.success("Comment added", "The ticket timeline has been updated.");
    } catch (commentError) {
      const message = commentError instanceof Error ? commentError.message : "Unable to add the comment.";
      toast.error("Comment failed", message);
    } finally {
      setIsSubmittingComment(false);
    }
  };

  const handleUpdateComment = async () => {
    if (!ticketId || editingCommentId == null || !editingCommentBody.trim()) {
      return;
    }
    try {
      await ticketsApi.updateComment(ticketId, editingCommentId, editingCommentBody.trim());
      setEditingCommentId(null);
      setEditingCommentBody("");
      await refreshDetail();
      toast.success("Comment updated", "Your edit is now live.");
    } catch (updateError) {
      const message = updateError instanceof Error ? updateError.message : "Unable to update the comment.";
      toast.error("Update failed", message);
    }
  };

  const handleDeleteComment = async (commentId: number) => {
    if (!ticketId) {
      return;
    }
    if (!window.confirm("Delete this comment?")) {
      return;
    }
    try {
      await ticketsApi.deleteComment(ticketId, commentId);
      await refreshDetail();
      toast.success("Comment deleted", "The comment was removed from the timeline.");
    } catch (deleteError) {
      const message = deleteError instanceof Error ? deleteError.message : "Unable to delete the comment.";
      toast.error("Delete failed", message);
    }
  };

  const handleDeleteAttachment = async (attachmentId: number) => {
    if (!window.confirm("Delete this attachment?")) {
      return;
    }
    try {
      await ticketsApi.deleteAttachment(attachmentId);
      await refreshDetail();
      toast.success("Attachment deleted", "The file was removed.");
    } catch (deleteError) {
      const message = deleteError instanceof Error ? deleteError.message : "Unable to delete the attachment.";
      toast.error("Delete failed", message);
    }
  };

  const handleCreateCategory = async () => {
    if (!admin) {
      return;
    }
    if (!quickCategoryName.trim()) {
      toast.error("Missing category name", "Type a category name before adding it.");
      return;
    }
    try {
      const response = await catalogApi.createCategory({
        name: quickCategoryName.trim(),
        color: "#6366f1",
        icon: "fa-tag",
      });
      const created = response.data as { id: number; name: string };
      setForm((current) => ({ ...current, category_id: String(created.id) }));
      setQuickCategoryName("");
      await refreshOptions();
      toast.success("Category added", created.name);
    } catch (createError) {
      const message = createError instanceof Error ? createError.message : "Unable to create the category.";
      toast.error("Create failed", message);
    }
  };

  const handleDeleteCategory = async () => {
    if (!admin || !form.category_id) {
      return;
    }
    const currentCategory = options?.categories.find((category) => String(category.id) === form.category_id);
    if (!window.confirm(`Delete category ${currentCategory?.name || "selected category"}?`)) {
      return;
    }
    try {
      await catalogApi.deleteCategory(Number(form.category_id));
      setForm((current) => ({ ...current, category_id: "" }));
      await refreshOptions();
      toast.success("Category deleted", currentCategory?.name || "The category was removed.");
    } catch (deleteError) {
      const message = deleteError instanceof Error ? deleteError.message : "Unable to delete the category.";
      toast.error("Delete failed", message);
    }
  };

  const handleCreateAssignee = async () => {
    if (!admin) {
      return;
    }
    if (!quickAssigneeName.trim()) {
      toast.error("Missing assignee name", "Type an assignee name before adding it.");
      return;
    }
    try {
      await catalogApi.createAssignee(quickAssigneeName.trim());
      setForm((current) => ({ ...current, staff_assigned: quickAssigneeName.trim() }));
      setQuickAssigneeName("");
      await refreshOptions();
      toast.success("Assignee added", "The assignee is now selectable.");
    } catch (createError) {
      const message = createError instanceof Error ? createError.message : "Unable to create the assignee.";
      toast.error("Create failed", message);
    }
  };

  const handleDeleteAssignee = async () => {
    if (!admin || !form.staff_assigned.trim()) {
      return;
    }
    const targetAssignee = form.staff_assigned.trim();
    if (!window.confirm(`Delete assignee ${targetAssignee}?`)) {
      return;
    }
    try {
      await catalogApi.deleteAssignee(targetAssignee);
      setForm((current) => ({ ...current, staff_assigned: "" }));
      await refreshOptions();
      toast.success("Assignee deleted", targetAssignee);
    } catch (deleteError) {
      const message = deleteError instanceof Error ? deleteError.message : "Unable to delete the assignee.";
      toast.error("Delete failed", message);
    }
  };

  if (isLoading) {
    return (
      <div className="ops-shell min-h-[100dvh] px-4 py-5 text-white sm:px-6 lg:px-8">
        <div className="mx-auto max-w-7xl rounded-[2rem] border border-zinc-800 bg-black/20 p-8">
          <div className="mono-data text-[11px] uppercase tracking-[0.28em] text-amber-300">Loading workspace</div>
          <div className="mt-4 text-sm text-zinc-400">Pulling ticket state, operators, categories, labels, and comments.</div>
        </div>
      </div>
    );
  }

  if (error || !options) {
    return (
      <div className="ops-shell min-h-[100dvh] px-4 py-5 text-white sm:px-6 lg:px-8">
        <div className="mx-auto max-w-7xl rounded-[2rem] border border-rose-500/20 bg-black/20 p-8">
          <div className="flex items-center gap-3 text-rose-300">
            <AlertTriangle className="h-5 w-5" />
            <span className="mono-data text-[11px] uppercase tracking-[0.28em]">Workspace unavailable</span>
          </div>
          <div className="mt-4 text-sm leading-7 text-zinc-300">{error || "The ticket workspace could not load."}</div>
        </div>
      </div>
    );
  }

  const comments = detail?.comments ?? [];
  const attachments = detail?.attachments ?? [];

  return (
    <div className="ops-shell min-h-[100dvh] px-4 py-5 text-white sm:px-6 lg:px-8">
      <div className="mx-auto max-w-7xl space-y-6">
        <div className="ops-glass rounded-[2rem] px-5 py-5 sm:px-7">
          <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
            <div className="min-w-0">
              <div className="mono-data text-[11px] uppercase tracking-[0.28em] text-amber-300">
                {ticketId ? "Ticket Workspace" : "New Ticket"}
              </div>
              <h1 className="mt-3 text-3xl font-semibold tracking-tight text-white">
                {ticketId ? detail?.ticket.title || ticketId : "Create a new operational ticket"}
              </h1>
              <p className="mt-3 max-w-3xl text-sm leading-7 text-zinc-400">
                This is the transactional workspace for the new Aether design: create, edit, attach files, discuss work,
                and move the ticket through its actual lifecycle.
              </p>
              <div className="mt-4 flex flex-wrap gap-2 text-xs text-zinc-400">
                {user ? (
                  <span className="rounded-full border border-zinc-700 bg-zinc-950/60 px-3 py-1.5">
                    Signed in as {user.display_name} · {roleLabels[user.role] || user.role}
                  </span>
                ) : null}
                {ticketId ? (
                  <span className="rounded-full border border-zinc-700 bg-zinc-950/60 px-3 py-1.5">
                    Ticket ID {ticketId}
                  </span>
                ) : null}
              </div>
            </div>

            <div className="flex flex-wrap gap-3">
              <Link
                href="/command-center"
                className="rounded-full border border-zinc-700/70 bg-zinc-950/60 px-4 py-2.5 text-sm font-medium text-zinc-200 transition hover:border-zinc-500"
              >
                Back to queue
              </Link>
              <Link
                href="/admin"
                className="rounded-full border border-zinc-700/70 bg-zinc-950/60 px-4 py-2.5 text-sm font-medium text-zinc-200 transition hover:border-zinc-500"
              >
                Admin console
              </Link>
              {ticketId ? (
                <button
                  type="button"
                  onClick={handleDeleteTicket}
                  className="inline-flex items-center gap-2 rounded-full border border-rose-400/20 bg-rose-500/10 px-4 py-2.5 text-sm font-medium text-rose-100 transition hover:bg-rose-500/20"
                >
                  <Trash2 className="h-4 w-4" />
                  Delete
                </button>
              ) : null}
              <button
                type="button"
                onClick={handleSaveTicket}
                disabled={isSaving}
                className="inline-flex items-center gap-2 rounded-full bg-amber-500 px-4 py-2.5 text-sm font-semibold text-black transition hover:bg-amber-400 disabled:cursor-not-allowed disabled:opacity-70"
              >
                <Save className="h-4 w-4" />
                {isSaving ? "Saving..." : ticketId ? "Save changes" : "Create ticket"}
              </button>
            </div>
          </div>
        </div>

        <div className="grid gap-6 xl:grid-cols-[1.15fr,0.85fr]">
          <section className="space-y-6">
            <div className="ops-card rounded-[1.75rem] p-6">
              <div className="flex items-center gap-3">
                <FileText className="h-5 w-5 text-amber-300" />
                <div>
                  <div className="text-lg font-semibold text-white">Ticket record</div>
                  <div className="mt-1 text-sm text-zinc-500">Create or update the operational facts that drive the queue.</div>
                </div>
              </div>

              <div className="mt-6 grid gap-4 md:grid-cols-2">
                <label className="block">
                  <span className="text-sm text-zinc-400">Title</span>
                  <input
                    value={form.title}
                    onChange={(event) => setForm((current) => ({ ...current, title: event.target.value }))}
                    className="mt-2 w-full rounded-2xl border border-zinc-700 bg-zinc-950/70 px-4 py-3 text-sm text-white outline-none transition focus:border-amber-400/50"
                    placeholder="Briefly describe the issue"
                  />
                </label>
                <label className="block">
                  <span className="text-sm text-zinc-400">Requester</span>
                  <input
                    value={form.requester}
                    onChange={(event) => setForm((current) => ({ ...current, requester: event.target.value }))}
                    className="mt-2 w-full rounded-2xl border border-zinc-700 bg-zinc-950/70 px-4 py-3 text-sm text-white outline-none transition focus:border-amber-400/50"
                    placeholder="Who raised the ticket?"
                  />
                </label>
                <label className="block">
                  <span className="text-sm text-zinc-400">Status</span>
                  <select
                    value={form.status}
                    onChange={(event) => setForm((current) => ({ ...current, status: event.target.value }))}
                    className="mt-2 w-full rounded-2xl border border-zinc-700 bg-zinc-950/70 px-4 py-3 text-sm text-white outline-none transition focus:border-amber-400/50"
                  >
                    {statuses.map((status) => (
                      <option key={status} value={status}>
                        {status}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="block">
                  <span className="text-sm text-zinc-400">Priority</span>
                  <select
                    value={form.priority}
                    onChange={(event) => setForm((current) => ({ ...current, priority: event.target.value }))}
                    className="mt-2 w-full rounded-2xl border border-zinc-700 bg-zinc-950/70 px-4 py-3 text-sm text-white outline-none transition focus:border-amber-400/50"
                  >
                    {priorities.map((priority) => (
                      <option key={priority} value={priority}>
                        {priority}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="block">
                  <span className="text-sm text-zinc-400">Category</span>
                  <select
                    value={form.category_id}
                    onChange={(event) => setForm((current) => ({ ...current, category_id: event.target.value }))}
                    className="mt-2 w-full rounded-2xl border border-zinc-700 bg-zinc-950/70 px-4 py-3 text-sm text-white outline-none transition focus:border-amber-400/50"
                  >
                    <option value="">No category</option>
                    {options.categories.map((category) => (
                      <option key={category.id} value={category.id}>
                        {category.name}
                      </option>
                    ))}
                  </select>
                  {admin ? (
                    <div className="mt-2 flex flex-wrap gap-2">
                      <input
                        value={quickCategoryName}
                        onChange={(event) => setQuickCategoryName(event.target.value)}
                        className="min-w-[180px] flex-1 rounded-full border border-zinc-700 bg-black/30 px-3 py-2 text-xs text-white"
                        placeholder="New category name"
                      />
                      <button
                        type="button"
                        onClick={handleCreateCategory}
                        className="rounded-full border border-zinc-700 bg-black/30 px-3 py-2 text-xs font-medium text-zinc-200 transition hover:border-zinc-500"
                      >
                        Add
                      </button>
                      <button
                        type="button"
                        onClick={handleDeleteCategory}
                        disabled={!form.category_id}
                        className="rounded-full border border-rose-400/20 bg-rose-500/10 px-3 py-2 text-xs font-medium text-rose-100 transition hover:bg-rose-500/20 disabled:cursor-not-allowed disabled:opacity-50"
                      >
                        Delete selected
                      </button>
                    </div>
                  ) : null}
                </label>
                <label className="block">
                  <span className="text-sm text-zinc-400">Assignee</span>
                  <select
                    value={form.staff_assigned}
                    onChange={(event) => setForm((current) => ({ ...current, staff_assigned: event.target.value }))}
                    className="mt-2 w-full rounded-2xl border border-zinc-700 bg-zinc-950/70 px-4 py-3 text-sm text-white outline-none transition focus:border-amber-400/50"
                  >
                    <option value="">Unassigned</option>
                    {currentAssignees.map((assignee) => (
                      <option key={assignee} value={assignee}>
                        {assignee}
                      </option>
                    ))}
                  </select>
                  {admin ? (
                    <div className="mt-2 flex flex-wrap gap-2">
                      <input
                        value={quickAssigneeName}
                        onChange={(event) => setQuickAssigneeName(event.target.value)}
                        className="min-w-[180px] flex-1 rounded-full border border-zinc-700 bg-black/30 px-3 py-2 text-xs text-white"
                        placeholder="New assignee name"
                      />
                      <button
                        type="button"
                        onClick={handleCreateAssignee}
                        className="rounded-full border border-zinc-700 bg-black/30 px-3 py-2 text-xs font-medium text-zinc-200 transition hover:border-zinc-500"
                      >
                        Add
                      </button>
                      <button
                        type="button"
                        onClick={handleDeleteAssignee}
                        disabled={!form.staff_assigned.trim()}
                        className="rounded-full border border-rose-400/20 bg-rose-500/10 px-3 py-2 text-xs font-medium text-rose-100 transition hover:bg-rose-500/20 disabled:cursor-not-allowed disabled:opacity-50"
                      >
                        Delete selected
                      </button>
                    </div>
                  ) : null}
                </label>
                <label className="block md:col-span-2">
                  <span className="text-sm text-zinc-400">Fallback request type</span>
                  <input
                    value={form.request_type}
                    onChange={(event) => setForm((current) => ({ ...current, request_type: event.target.value }))}
                    className="mt-2 w-full rounded-2xl border border-zinc-700 bg-zinc-950/70 px-4 py-3 text-sm text-white outline-none transition focus:border-amber-400/50"
                    placeholder="Used if you intentionally leave category unset"
                  />
                </label>
                <label className="block md:col-span-2">
                  <span className="text-sm text-zinc-400">Site / Asset Context</span>
                  <input
                    value={form.site_id}
                    onChange={(event) => setForm((current) => ({ ...current, site_id: event.target.value }))}
                    className="mt-2 w-full rounded-2xl border border-zinc-700 bg-zinc-950/70 px-4 py-3 text-sm text-white outline-none transition focus:border-amber-400/50"
                    placeholder="Optional site, asset, or tenant reference"
                  />
                </label>
                <label className="block md:col-span-2">
                  <span className="text-sm text-zinc-400">Description</span>
                  <textarea
                    value={form.description}
                    onChange={(event) => setForm((current) => ({ ...current, description: event.target.value }))}
                    className="mt-2 min-h-[160px] w-full rounded-2xl border border-zinc-700 bg-zinc-950/70 px-4 py-3 text-sm text-white outline-none transition focus:border-amber-400/50"
                    placeholder="Capture the actual operating context, error, and request details."
                  />
                </label>
                <label className="block md:col-span-2">
                  <span className="text-sm text-zinc-400">Resolution notes</span>
                  <textarea
                    value={form.resolution_notes}
                    onChange={(event) => setForm((current) => ({ ...current, resolution_notes: event.target.value }))}
                    className="mt-2 min-h-[120px] w-full rounded-2xl border border-zinc-700 bg-zinc-950/70 px-4 py-3 text-sm text-white outline-none transition focus:border-amber-400/50"
                    placeholder="Document what fixed it, what remains open, or what operators should know."
                  />
                </label>
              </div>

              <div className="mt-6">
                <div className="text-sm text-zinc-400">Labels</div>
                <div className="mt-3 flex flex-wrap gap-2">
                  {currentLabels.map((label) => {
                    const active = form.label_ids.includes(label.id);
                    return (
                      <button
                        key={label.id}
                        type="button"
                        onClick={() =>
                          setForm((current) => ({
                            ...current,
                            label_ids: active
                              ? current.label_ids.filter((labelId) => labelId !== label.id)
                              : [...current.label_ids, label.id],
                          }))
                        }
                        className={`rounded-full border px-3 py-2 text-xs font-medium transition ${
                          active
                            ? "border-amber-400/30 bg-amber-500/12 text-amber-100"
                            : "border-zinc-700 bg-zinc-950/60 text-zinc-300 hover:border-zinc-500"
                        }`}
                        style={!active ? undefined : { boxShadow: `inset 0 0 0 1px ${label.color}55` }}
                      >
                        {label.name}
                      </button>
                    );
                  })}
                </div>
              </div>
            </div>

            <div className="ops-card rounded-[1.75rem] p-6">
              <div className="flex items-center gap-3">
                <Paperclip className="h-5 w-5 text-amber-300" />
                <div>
                  <div className="text-lg font-semibold text-white">Ticket files</div>
                  <div className="mt-1 text-sm text-zinc-500">Attach screenshots, PDFs, and text files directly to the ticket.</div>
                </div>
              </div>

              <div className="mt-6">
                <FileDropzone files={ticketFiles} onChange={setTicketFiles} label="Add files to this ticket" />
              </div>

              {attachments.length ? (
                <div className="mt-6 grid gap-3">
                  {attachments.map((attachment) => (
                    <div key={attachment.id} className="rounded-[1.25rem] border border-zinc-800 bg-zinc-950/60 p-4">
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0">
                          <a
                            href={attachmentLink(attachment)}
                            target="_blank"
                            rel="noreferrer"
                            className="truncate text-sm font-medium text-amber-100 hover:text-amber-200"
                          >
                            {attachment.original_name}
                          </a>
                          <div className="mt-1 text-xs text-zinc-500">
                            {formatFileSize(attachment.file_size)} · {formatRelativeDate(attachment.created_at)}
                          </div>
                        </div>
                        {writable ? (
                          <button
                            type="button"
                            onClick={() => handleDeleteAttachment(attachment.id)}
                            className="inline-flex h-9 w-9 items-center justify-center rounded-full border border-zinc-700 bg-black/30 text-zinc-400 transition hover:border-rose-400/40 hover:text-rose-200"
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        ) : null}
                      </div>
                      {isImageAttachment(attachment) ? (
                        <Image
                          src={attachmentLink(attachment)}
                          alt={attachment.original_name}
                          width={1200}
                          height={900}
                          unoptimized
                          className="mt-4 max-h-56 rounded-2xl border border-zinc-800 object-cover"
                        />
                      ) : null}
                    </div>
                  ))}
                </div>
              ) : null}
            </div>
          </section>

          <section className="space-y-6">
            <div className="ops-card rounded-[1.75rem] p-6">
              <div className="flex items-center gap-3">
                <MessageSquare className="h-5 w-5 text-amber-300" />
                <div>
                  <div className="text-lg font-semibold text-white">Comments and worklog</div>
                  <div className="mt-1 text-sm text-zinc-500">Use comments as the collaborative timeline for the ticket.</div>
                </div>
              </div>

              <div className="mt-6 space-y-4">
                <textarea
                  value={commentBody}
                  onChange={(event) => setCommentBody(event.target.value)}
                  className="min-h-[120px] w-full rounded-2xl border border-zinc-700 bg-zinc-950/70 px-4 py-3 text-sm text-white outline-none transition focus:border-amber-400/50"
                  placeholder="Add a meaningful update, next step, diagnostic note, or customer-facing summary."
                />
                <FileDropzone files={commentFiles} onChange={setCommentFiles} label="Attach files to this comment" />
                <button
                  type="button"
                  onClick={handleSubmitComment}
                  disabled={isSubmittingComment}
                  className="inline-flex items-center gap-2 rounded-full bg-cyan-400 px-4 py-2.5 text-sm font-semibold text-slate-950 transition hover:bg-cyan-300 disabled:cursor-not-allowed disabled:opacity-70"
                >
                  <Plus className="h-4 w-4" />
                  {isSubmittingComment ? "Posting..." : "Add comment"}
                </button>
              </div>

              <div className="mt-6 space-y-4">
                {comments.length ? (
                  comments.map((comment) => (
                    <div key={comment.id} className="rounded-[1.25rem] border border-zinc-800 bg-zinc-950/60 p-4">
                      <div className="flex items-start justify-between gap-4">
                        <div>
                          <div className="text-sm font-semibold text-white">{comment.author_display_name}</div>
                          <div className="mt-1 text-xs text-zinc-500">{formatRelativeDate(comment.created_at)}</div>
                        </div>
                        {writable && (user?.username === comment.author_username || admin) ? (
                          <div className="flex gap-2">
                            <button
                              type="button"
                              onClick={() => {
                                setEditingCommentId(comment.id);
                                setEditingCommentBody(comment.body);
                              }}
                              className="rounded-full border border-zinc-700 bg-black/30 px-3 py-1.5 text-xs text-zinc-300 transition hover:border-zinc-500"
                            >
                              Edit
                            </button>
                            <button
                              type="button"
                              onClick={() => handleDeleteComment(comment.id)}
                              className="rounded-full border border-rose-400/20 bg-rose-500/10 px-3 py-1.5 text-xs text-rose-100 transition hover:bg-rose-500/20"
                            >
                              Delete
                            </button>
                          </div>
                        ) : null}
                      </div>
                      {editingCommentId === comment.id ? (
                        <div className="mt-4 space-y-3">
                          <textarea
                            value={editingCommentBody}
                            onChange={(event) => setEditingCommentBody(event.target.value)}
                            className="min-h-[100px] w-full rounded-2xl border border-zinc-700 bg-black/30 px-4 py-3 text-sm text-white outline-none transition focus:border-amber-400/50"
                          />
                          <div className="flex gap-2">
                            <button
                              type="button"
                              onClick={handleUpdateComment}
                              className="rounded-full bg-amber-500 px-4 py-2 text-sm font-semibold text-black transition hover:bg-amber-400"
                            >
                              Save edit
                            </button>
                            <button
                              type="button"
                              onClick={() => {
                                setEditingCommentId(null);
                                setEditingCommentBody("");
                              }}
                              className="rounded-full border border-zinc-700 bg-zinc-950/60 px-4 py-2 text-sm font-medium text-zinc-300 transition hover:border-zinc-500"
                            >
                              Cancel
                            </button>
                          </div>
                        </div>
                      ) : (
                        <p className="mt-4 text-sm leading-7 text-zinc-300">{comment.body}</p>
                      )}
                      {comment.attachments.length ? (
                        <div className="mt-4 grid gap-3">
                          {comment.attachments.map((attachment) => (
                            <div key={attachment.id} className="rounded-2xl border border-zinc-800 bg-black/20 p-3">
                              <div className="flex items-start justify-between gap-3">
                                <div className="min-w-0">
                                  <a
                                    href={attachmentLink(attachment)}
                                    target="_blank"
                                    rel="noreferrer"
                                    className="truncate text-sm font-medium text-cyan-100 hover:text-cyan-200"
                                  >
                                    {attachment.original_name}
                                  </a>
                                  <div className="mt-1 text-xs text-zinc-500">
                                    {formatFileSize(attachment.file_size)} · {formatRelativeDate(attachment.created_at)}
                                  </div>
                                </div>
                                {writable ? (
                                  <button
                                    type="button"
                                    onClick={() => handleDeleteAttachment(attachment.id)}
                                    className="inline-flex h-8 w-8 items-center justify-center rounded-full border border-zinc-700 bg-black/30 text-zinc-400 transition hover:border-rose-400/40 hover:text-rose-200"
                                  >
                                    <Trash2 className="h-4 w-4" />
                                  </button>
                                ) : null}
                              </div>
                              {isImageAttachment(attachment) ? (
                                <Image
                                  src={attachmentLink(attachment)}
                                  alt={attachment.original_name}
                                  width={1200}
                                  height={900}
                                  unoptimized
                                  className="mt-3 max-h-48 rounded-xl border border-zinc-800 object-cover"
                                />
                              ) : null}
                            </div>
                          ))}
                        </div>
                      ) : null}
                    </div>
                  ))
                ) : (
                  <div className="rounded-[1.25rem] border border-dashed border-zinc-700 bg-zinc-950/50 px-4 py-5 text-sm leading-7 text-zinc-500">
                    No comments yet. This ticket still needs its collaborative worklog.
                  </div>
                )}
              </div>
            </div>

            {detail ? (
              <div className="ops-card rounded-[1.75rem] p-6">
                <div className="flex items-center gap-3">
                  <Shield className="h-5 w-5 text-amber-300" />
                  <div>
                    <div className="text-lg font-semibold text-white">Timeline and intelligence</div>
                    <div className="mt-1 text-sm text-zinc-500">Operational context stays visible beside the transactional workflow.</div>
                  </div>
                </div>

                <div className="mt-6 space-y-4">
                  {detail.events.map((event) => (
                    <div key={`${event.event_type}-${event.event_ts}-${event.actor_id || ""}`} className="rounded-2xl border border-zinc-800 bg-zinc-950/60 p-4">
                      <div className="text-sm font-semibold text-white">{event.event_type.replaceAll("_", " ")}</div>
                      <div className="mt-1 text-xs text-zinc-500">
                        {formatRelativeDate(event.event_ts)} · {event.actor_id || event.actor_type}
                      </div>
                      {event.payload ? (
                        <pre className="mono-data mt-3 overflow-x-auto rounded-xl border border-zinc-800 bg-black/30 p-3 text-[11px] text-zinc-400">
                          {JSON.stringify(event.payload, null, 2)}
                        </pre>
                      ) : null}
                    </div>
                  ))}
                </div>
              </div>
            ) : null}
          </section>
        </div>
      </div>
    </div>
  );
}
