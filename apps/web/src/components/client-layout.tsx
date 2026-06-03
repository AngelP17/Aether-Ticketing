"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { AuthGate } from "@/components/auth-gate";
import { NotificationProvider, ToastContainer, useNotifications } from "@/components/notifications";

function ToastViewport() {
  const { notifications, clearNotification } = useNotifications();
  return (
    <>
      <ToastContainer toasts={notifications.slice(0, 5)} onRemove={clearNotification} />
    </>
  );
}

function GlobalKeyboardShortcuts() {
  const router = useRouter();

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const isMac = /Mac|iPod|iPhone|iPad/.test(navigator.platform);
      const mod = isMac ? e.metaKey : e.ctrlKey;

      // Cmd/Ctrl + N : new ticket (high impact shortcut)
      if (mod && e.key.toLowerCase() === "n") {
        e.preventDefault();
        router.push("/tickets/new");
        return;
      }

      // Cmd/Ctrl + K : jump to command center (primary search / queue surface)
      if (mod && e.key.toLowerCase() === "k") {
        e.preventDefault();
        router.push("/command-center");
        return;
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [router]);

  return null;
}

export default function ClientLayout({ children }: { children: React.ReactNode }) {
  return (
    <NotificationProvider>
      <AuthGate>
        {children}
      </AuthGate>
      <ToastViewport />
      <GlobalKeyboardShortcuts />
    </NotificationProvider>
  );
}
