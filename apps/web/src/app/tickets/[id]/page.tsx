import { TicketWorkspace } from "@/components/ticket-workspace";

export const dynamic = "force-dynamic";

export default function TicketPage({ params }: { params: { id: string } }) {
  return <TicketWorkspace ticketId={params.id} />;
}
