"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { Plus } from "lucide-react";

import { OpsShell } from "@/components/ops-shell";
import { TicketWorkspace } from "@/components/ticket-workspace";

export default function TicketPage() {
  const params = useParams<{ id: string }>();
  const ticketId = params?.id ?? "";

  return (
    <OpsShell
      eyebrow="Aether OpsCenter"
      title="Ticket Detail"
      subtitle={ticketId ? `Ticket ${ticketId}` : "Ticket workspace"}
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
      <TicketWorkspace ticketId={ticketId} />
    </OpsShell>
  );
}
