"use client";

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

export default function ClientLayout({ children }: { children: React.ReactNode }) {
  return (
    <NotificationProvider>
      <AuthGate>
        {children}
      </AuthGate>
      <ToastViewport />
    </NotificationProvider>
  );
}
