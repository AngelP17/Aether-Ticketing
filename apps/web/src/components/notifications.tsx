"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { CheckCircle, AlertCircle, Info, Bell, X } from "lucide-react";

type NotificationType = "success" | "error" | "warning" | "info";

type Notification = {
  id: string;
  type: NotificationType;
  title: string;
  message: string | undefined;
  timestamp: Date;
  read: boolean;
};

type StoredNotification = Omit<Notification, "timestamp"> & {
  timestamp: string;
};

type NotificationContextType = {
  notifications: Notification[];
  unreadCount: number;
  addNotification: (type: NotificationType, title: string, message?: string) => void;
  markAsRead: (id: string) => void;
  markAllAsRead: () => void;
  clearNotification: (id: string) => void;
  clearAll: () => void;
};

const NotificationContext = createContext<NotificationContextType | null>(null);
const STORAGE_KEY = "aether.notifications.v1";
const TOAST_LIFETIME_MS = 4000;
const MAX_NOTIFICATIONS = 50;

function isNotificationType(value: unknown): value is NotificationType {
  return value === "success" || value === "error" || value === "warning" || value === "info";
}

function serializeNotifications(notifications: Notification[]) {
  return JSON.stringify(
    notifications.map((notification) => ({
      ...notification,
      timestamp: notification.timestamp.toISOString(),
    }))
  );
}

function deserializeNotifications(rawValue: string) {
  try {
    const parsed = JSON.parse(rawValue) as Partial<StoredNotification>[];
    if (!Array.isArray(parsed)) {
      return [];
    }

    return parsed
      .map((notification): Notification | null => {
        if (
          !notification ||
          typeof notification.id !== "string" ||
          !isNotificationType(notification.type) ||
          typeof notification.title !== "string" ||
          typeof notification.timestamp !== "string" ||
          typeof notification.read !== "boolean"
        ) {
          return null;
        }

        const timestamp = new Date(notification.timestamp);
        if (Number.isNaN(timestamp.getTime())) {
          return null;
        }

        return {
          id: notification.id,
          type: notification.type,
          title: notification.title,
          message: typeof notification.message === "string" ? notification.message : undefined,
          timestamp,
          read: notification.read,
        };
      })
      .filter((notification): notification is Notification => notification !== null)
      .sort((left, right) => right.timestamp.getTime() - left.timestamp.getTime())
      .slice(0, MAX_NOTIFICATIONS);
  } catch {
    return [];
  }
}

export function useNotifications() {
  const context = useContext(NotificationContext);
  if (!context) {
    throw new Error("useNotifications must be used within NotificationProvider");
  }
  return context;
}

export function NotificationProvider({ children }: { children: ReactNode }) {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [isHydrated, setIsHydrated] = useState(false);

  const unreadCount = notifications.filter((n) => !n.read).length;

  useEffect(() => {
    try {
      const storedNotifications = window.localStorage.getItem(STORAGE_KEY);
      if (storedNotifications) {
        setNotifications(deserializeNotifications(storedNotifications));
      }
    } catch {
      // Ignore storage access issues and fall back to in-memory notifications.
    } finally {
      setIsHydrated(true);
    }
  }, []);

  useEffect(() => {
    if (!isHydrated) {
      return;
    }

    try {
      if (notifications.length === 0) {
        window.localStorage.removeItem(STORAGE_KEY);
      } else {
        window.localStorage.setItem(STORAGE_KEY, serializeNotifications(notifications));
      }
    } catch {
      // Ignore storage write issues; notifications still work in memory.
    }
  }, [isHydrated, notifications]);

  const addNotification = useCallback(
    (type: NotificationType, title: string, message?: string) => {
      // Coalesce identical errors raised in quick succession (e.g. a useEffect
      // loop that re-fires the same toast on every render). The dedupe key
      // uses the first 750 ms after a notification is added as the window
      // for a re-entry, which is enough to swallow the re-render storm
      // while still allowing a distinct retry to surface later.
      setNotifications((prev) => {
        const dedupeKey = `${type}::${title}::${message ?? ""}`;
        const now = Date.now();
        const lastDuplicate = prev.find(
          (n) => `${n.type}::${n.title}::${n.message ?? ""}` === dedupeKey && now - n.timestamp.getTime() < 750,
        );
        if (lastDuplicate) {
          return prev;
        }
        const id = `notif-${now}-${Math.random().toString(36).slice(2, 11)}`;
        const notification: Notification = {
          id,
          type,
          title,
          message,
          timestamp: new Date(),
          read: false,
        };
        return [notification, ...prev].slice(0, MAX_NOTIFICATIONS);
      });
    },
    []
  );

  const markAsRead = useCallback((id: string) => {
    setNotifications((prev) =>
      prev.map((n) => (n.id === id ? { ...n, read: true } : n))
    );
  }, []);

  const markAllAsRead = useCallback(() => {
    setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
  }, []);

  const clearNotification = useCallback((id: string) => {
    setNotifications((prev) => prev.filter((n) => n.id !== id));
  }, []);

  const clearAll = useCallback(() => {
    setNotifications([]);
  }, []);

  return (
    <NotificationContext.Provider
      value={{
        notifications,
        unreadCount,
        addNotification,
        markAsRead,
        markAllAsRead,
        clearNotification,
        clearAll,
      }}
    >
      {children}
    </NotificationContext.Provider>
  );
}

const typeStyles: Record<NotificationType, { bg: string; border: string; icon: typeof CheckCircle }> = {
  success: { bg: "bg-emerald-500/10", border: "border-emerald-500/30", icon: CheckCircle },
  error: { bg: "bg-rose-500/10", border: "border-rose-500/30", icon: AlertCircle },
  warning: { bg: "bg-amber-500/10", border: "border-amber-500/30", icon: AlertCircle },
  info: { bg: "bg-cyan-500/10", border: "border-cyan-500/30", icon: Info },
};

const typeColors: Record<NotificationType, string> = {
  success: "text-emerald-400",
  error: "text-rose-400",
  warning: "text-amber-400",
  info: "text-cyan-400",
};

function formatTime(date: Date): string {
  const now = new Date();
  const diff = now.getTime() - date.getTime();
  const minutes = Math.floor(diff / 60000);
  const hours = Math.floor(diff / 3600000);

  if (minutes < 1) return "Just now";
  if (minutes < 60) return `${minutes}m ago`;
  if (hours < 24) return `${hours}h ago`;
  return date.toLocaleDateString();
}

interface NotificationBellProps {
  className?: string;
}

export function NotificationBell({ className = "" }: NotificationBellProps) {
  const { notifications, unreadCount, markAsRead, markAllAsRead, clearNotification } =
    useNotifications();
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className={`relative ${className}`}>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="relative flex h-9 w-9 items-center justify-center rounded-lg border border-zinc-800 bg-black/20 text-zinc-400 transition hover:border-zinc-700 hover:text-zinc-200"
        aria-label={`Notifications${unreadCount > 0 ? ` (${unreadCount} unread)` : ""}`}
      >
        <Bell className="h-4 w-4" />
        {unreadCount > 0 && (
          <span className="absolute -right-1 -top-1 flex h-4 w-4 items-center justify-center rounded-full bg-amber-500 text-[10px] font-bold text-black">
            {unreadCount > 9 ? "9+" : unreadCount}
          </span>
        )}
      </button>

      {isOpen && (
        <>
          <div
            className="fixed inset-0 z-40"
            onClick={() => setIsOpen(false)}
          />
          <div className="absolute right-0 top-full z-50 mt-2 w-80 rounded-xl border border-zinc-800 bg-[#0a0a0d]/95 backdrop-blur-xl shadow-2xl">
            <div className="flex items-center justify-between border-b border-zinc-800 px-4 py-3">
              <h3 className="text-sm font-semibold text-zinc-100">Notifications</h3>
              <div className="flex items-center gap-2">
                {unreadCount > 0 && (
                  <button
                    type="button"
                    onClick={markAllAsRead}
                    className="text-xs text-amber-400 hover:text-amber-300"
                  >
                    Mark all read
                  </button>
                )}
                <button
                  type="button"
                  onClick={() => setIsOpen(false)}
                  className="text-zinc-500 hover:text-zinc-300"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
            </div>

            <div className="max-h-80 overflow-y-auto">
              {notifications.length === 0 ? (
                <div className="px-4 py-8 text-center text-sm text-zinc-500">
                  No notifications yet
                </div>
              ) : (
                notifications.map((notif) => {
                  const Icon = typeStyles[notif.type].icon;
                  return (
                    <div
                      key={notif.id}
                      className={`relative border-b border-zinc-800/50 px-4 py-3 transition hover:bg-zinc-900/30 ${
                        !notif.read ? "bg-zinc-900/20" : ""
                      }`}
                      onClick={() => markAsRead(notif.id)}
                    >
                      <div className="flex gap-3">
                        <div
                          className={`mt-0.5 rounded-lg p-1.5 ${
                            typeStyles[notif.type].bg
                          }`}
                        >
                          <Icon
                            className={`h-3.5 w-3.5 ${typeColors[notif.type]}`}
                          />
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-start justify-between gap-2">
                            <p className="text-sm font-medium text-zinc-100 truncate">
                              {notif.title}
                            </p>
                            <span className="text-[10px] text-zinc-600 whitespace-nowrap">
                              {formatTime(notif.timestamp)}
                            </span>
                          </div>
                          {notif.message && (
                            <p className="mt-0.5 text-xs text-zinc-400 line-clamp-2">
                              {notif.message}
                            </p>
                          )}
                        </div>
                      </div>
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          clearNotification(notif.id);
                        }}
                        className="absolute right-2 top-2 text-zinc-600 hover:text-zinc-400"
                      >
                        <X className="h-3 w-3" />
                      </button>
                      {!notif.read && (
                        <span className="absolute left-1.5 top-1/2 -translate-y-1/2 h-1.5 w-1.5 rounded-full bg-amber-500" />
                      )}
                    </div>
                  );
                })
              )}
            </div>

            {notifications.length > 0 && (
              <div className="border-t border-zinc-800 px-4 py-2">
                <button
                  type="button"
                  onClick={() => {
                    markAllAsRead();
                    setIsOpen(false);
                  }}
                  className="w-full text-center text-xs text-zinc-500 hover:text-zinc-300"
                >
                  Clear all after reading
                </button>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}

interface ToastProps {
  id: string;
  type: NotificationType;
  title: string;
  message?: string;
  onClose: (id: string) => void;
}

function Toast({ id, type, title, message, onClose }: ToastProps) {
  const Icon = typeStyles[type].icon;

  return (
    <div
      className={`pointer-events-auto slide-in flex w-80 items-start gap-3 rounded-xl border px-4 py-3 shadow-xl transition-all ${
        typeStyles[type].bg
      } ${typeStyles[type].border}`}
    >
      <Icon className={`h-4 w-4 shrink-0 mt-0.5 ${typeColors[type]}`} />
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-zinc-100">{title}</p>
        {message && (
          <p className="mt-0.5 text-xs text-zinc-400">{message}</p>
        )}
      </div>
      <button
        onClick={() => onClose(id)}
        className="text-zinc-500 hover:text-zinc-300"
      >
        <X className="h-4 w-4" />
      </button>
    </div>
  );
}

interface ToastContainerProps {
  toasts: Notification[];
  onRemove: (id: string) => void;
}

export function ToastContainer({ toasts, onRemove }: ToastContainerProps) {
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    const interval = window.setInterval(() => {
      setNow(Date.now());
    }, 1000);

    return () => window.clearInterval(interval);
  }, []);

  const visibleToasts = toasts.filter((toast) => now - toast.timestamp.getTime() < TOAST_LIFETIME_MS);

  return (
    <div
      className="pointer-events-none fixed right-4 top-4 z-[100] flex flex-col gap-2"
      role="status"
      aria-live="polite"
      aria-atomic="true"
    >
      {visibleToasts.map((toast) => (
        <Toast
          key={toast.id}
          id={toast.id}
          type={toast.type}
          title={toast.title}
          message={toast.message}
          onClose={onRemove}
        />
      ))}
    </div>
  );
}

export function useToast() {
  const context = useContext(NotificationContext);

  const toast = useCallback(
    (type: NotificationType, title: string, message?: string) => {
      if (context) {
        context.addNotification(type, title, message);
      }
    },
    [context]
  );

  // Memoize the returned object so consumers can list it in a useEffect
  // dependency array without re-firing every render. The previous shape
  // returned a fresh object literal each call, which made useEffect loops
  // (and any useCallback that captured toast) re-run on every render.
  return useMemo(
    () => ({
      success: (title: string, message?: string) => toast("success", title, message),
      error: (title: string, message?: string) => toast("error", title, message),
      warning: (title: string, message?: string) => toast("warning", title, message),
      info: (title: string, message?: string) => toast("info", title, message),
    }),
    [toast],
  );
}
