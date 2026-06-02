"use client";

import { useState, useEffect, useCallback } from "react";
import Image from "next/image";
import { useRouter } from "next/navigation";
import {
  User,
  Lock,
  Eye,
  EyeOff,
  AlertCircle,
  Loader2,
} from "lucide-react";
import { useToast } from "@/components/notifications";
import { ACCESS_TOKEN_KEY, USER_STORAGE_KEY } from "@/lib/auth";

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errors, setErrors] = useState<{ username?: string; password?: string; general?: string }>({});
  const [greeting, setGreeting] = useState("Good morning");
  const toast = useToast();

  useEffect(() => {
    const hour = new Date().getHours();
    if (hour < 12) setGreeting("Good morning");
    else if (hour < 17) setGreeting("Good afternoon");
    else setGreeting("Good evening");
  }, []);

  const clearErrors = useCallback(() => {
    setErrors({});
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (isSubmitting) return;

    clearErrors();

    let hasError = false;

    if (!username.trim()) {
      setErrors((prev) => ({ ...prev, username: "Username is required" }));
      hasError = true;
    } else if (username.length < 2) {
      setErrors((prev) => ({ ...prev, username: "Username must be at least 2 characters" }));
      hasError = true;
    }

    if (!password) {
      setErrors((prev) => ({ ...prev, password: "Password is required" }));
      hasError = true;
    }

    if (hasError) return;

    setIsSubmitting(true);

    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "/api"}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });

      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.detail || "Invalid credentials");
      }

      const data = await response.json();

      localStorage.setItem(ACCESS_TOKEN_KEY, data.access_token);
      localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(data.user));

      toast.success("Authenticated successfully");

      await new Promise(resolve => setTimeout(resolve, 800));
      router.push("/command-center");
    } catch (err) {
      const message = err instanceof Error ? err.message : "Authentication failed";
      setErrors((prev) => ({ ...prev, general: message }));

      const form = document.getElementById("login-form");
      if (form) {
        form.classList.remove("shake");
        void (form as HTMLElement).offsetWidth;
        form.classList.add("shake");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-dvh flex">
      <style jsx>{`
        :root {
          --bg-deep: #09090b;
          --bg-surface: #141417;
          --bg-elevated: #1c1c21;
          --border-subtle: rgba(63, 63, 70, 0.25);
          --border-default: rgba(63, 63, 70, 0.45);
          --text-primary: #fafafa;
          --text-secondary: #a1a1aa;
          --text-muted: #52525b;
          --accent: #f59e0b;
          --accent-dim: rgba(245, 158, 11, 0.08);
          --cyan: #06b6d4;
          --emerald: #22c55e;
          --rose: #f43f5e;
        }
        * {
          box-sizing: border-box;
          margin: 0;
          padding: 0;
        }
        body {
          font-family: var(--font-display), sans-serif;
          background: var(--bg-deep);
          color: var(--text-primary);
        }
        ::selection {
          background: rgba(245, 158, 11, 0.25);
          color: #fafafa;
        }
        *:focus-visible {
          outline: 2px solid rgba(245, 158, 11, 0.4);
          outline-offset: 2px;
        }
        .bg-grid {
          position: fixed;
          inset: 0;
          pointer-events: none;
          z-index: 0;
          background-image: linear-gradient(rgba(245, 158, 11, 0.02) 1px, transparent 1px),
            linear-gradient(90deg, rgba(245, 158, 11, 0.02) 1px, transparent 1px);
          background-size: 48px 48px;
        }
        .scan-line {
          position: fixed;
          left: 0;
          right: 0;
          height: 1px;
          pointer-events: none;
          z-index: 1;
          background: linear-gradient(
            90deg,
            transparent 5%,
            rgba(245, 158, 11, 0.04) 50%,
            transparent 95%
          );
          animation: scanDown 8s linear infinite;
        }
        @keyframes scanDown {
          0% {
            top: -2px;
          }
          100% {
            top: 100vh;
          }
        }
        .glow-orb {
          position: absolute;
          border-radius: 50%;
          pointer-events: none;
          filter: blur(80px);
          opacity: 0;
          animation: orbFadeIn 2s ease forwards;
        }
        @keyframes orbFadeIn {
          to {
            opacity: 1;
          }
        }
        .glow-orb-1 {
          width: 320px;
          height: 320px;
          top: 15%;
          left: 20%;
          background: radial-gradient(circle, rgba(245, 158, 11, 0.1) 0%, transparent 70%);
          animation-delay: 0.3s;
        }
        .glow-orb-2 {
          width: 260px;
          height: 260px;
          bottom: 20%;
          right: 25%;
          background: radial-gradient(circle, rgba(6, 182, 212, 0.06) 0%, transparent 70%);
          animation-delay: 0.6s;
        }
        @keyframes orbFloat {
          0%,
          100% {
            transform: translate(0, 0);
          }
          33% {
            transform: translate(20px, -15px);
          }
          66% {
            transform: translate(-15px, 10px);
          }
        }
        .glow-orb-3 {
          width: 200px;
          height: 200px;
          top: 40%;
          left: 60%;
          background: radial-gradient(circle, rgba(245, 158, 11, 0.05) 0%, transparent 70%);
          animation-delay: 0.9s;
          animation: orbFloat 20s ease-in-out infinite, orbFadeIn 2s ease forwards;
        }
        .left-panel {
          display: flex;
          flex-direction: column;
          justify-content: space-between;
          width: 52%;
          padding: 3rem 4rem;
          position: relative;
          overflow: hidden;
        }
        @media (max-width: 767px) {
          .left-panel {
            display: none !important;
          }
          .right-panel {
            border-left: none !important;
          }
        }
        .status-dot {
          position: relative;
          display: inline-flex;
        }
        .status-dot::before {
          content: "";
          position: absolute;
          inset: 0;
          border-radius: 50%;
          background: inherit;
          animation: statusPulse 2s ease-out infinite;
          opacity: 0;
        }
        @keyframes statusPulse {
          0% {
            transform: scale(1);
            opacity: 0.6;
          }
          100% {
            transform: scale(2.5);
            opacity: 0;
          }
        }
        .fade-up {
          opacity: 1;
          transform: translateY(0);
        }
        @media (prefers-reduced-motion: no-preference) {
          .fade-up {
            animation: fadeUp 0.6s ease both;
          }
          @keyframes fadeUp {
            from {
              opacity: 0;
              transform: translateY(16px);
            }
            to {
              opacity: 1;
              transform: translateY(0);
            }
          }
        }
        .delay-1 {
          animation-delay: 0.1s;
        }
        .delay-2 {
          animation-delay: 0.2s;
        }
        .delay-3 {
          animation-delay: 0.3s;
        }
        .delay-4 {
          animation-delay: 0.4s;
        }
        .delay-5 {
          animation-delay: 0.5s;
        }
        .delay-6 {
          animation-delay: 0.6s;
        }
        .delay-7 {
          animation-delay: 0.7s;
        }
        .right-panel {
          flex: 1;
          display: flex;
          align-items: center;
          justify-content: center;
          padding: 1.5rem 3rem;
          position: relative;
          background: rgba(9, 9, 11, 0.4);
          backdrop-filter: blur(8px);
          border-left: 1px solid var(--border-subtle);
        }
        @media (max-width: 767px) {
          .right-panel {
            padding: 1.5rem;
          }
        }
        .form-input {
          width: 100%;
          padding: 12px 16px 12px 44px;
          background: rgba(20, 20, 23, 0.7);
          border: 1px solid var(--border-subtle);
          border-radius: 10px;
          color: var(--text-primary);
          font-size: 14px;
          font-family: var(--font-display), sans-serif;
          transition: border-color 0.25s, background 0.25s, box-shadow 0.25s;
        }
        .form-input::placeholder {
          color: var(--text-muted);
        }
        .form-input:hover {
          border-color: var(--border-default);
          background: rgba(20, 20, 23, 0.9);
        }
        .form-input:focus {
          outline: none;
          border-color: rgba(245, 158, 11, 0.4);
          background: rgba(24, 24, 27, 0.9);
          box-shadow: 0 0 0 3px rgba(245, 158, 11, 0.08);
        }
        .form-input.error {
          border-color: rgba(244, 63, 94, 0.5);
          box-shadow: 0 0 0 3px rgba(244, 63, 94, 0.06);
        }
        .btn-submit {
          width: 100%;
          padding: 13px 24px;
          border: none;
          border-radius: 10px;
          background: var(--accent);
          color: #000;
          font-size: 15px;
          font-family: var(--font-display), sans-serif;
          font-weight: 600;
          cursor: pointer;
          position: relative;
          overflow: hidden;
          transition: all 0.25s;
          box-shadow: 0 4px 16px rgba(245, 158, 11, 0.15);
        }
        .btn-submit:hover:not(:disabled) {
          transform: translateY(-1px);
          box-shadow: 0 8px 24px rgba(245, 158, 11, 0.25);
        }
        .btn-submit:active:not(:disabled) {
          transform: translateY(0);
        }
        .btn-submit:disabled {
          opacity: 0.7;
          cursor: not-allowed;
        }
        .btn-shimmer {
          position: absolute;
          top: 0;
          left: -100%;
          width: 100%;
          height: 100%;
          background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.15), transparent);
          transition: left 0.5s;
        }
        .btn-submit:hover:not(:disabled) .btn-shimmer {
          left: 100%;
        }
        .error-msg {
          font-size: 12px;
          color: var(--rose);
          margin-top: 6px;
          display: flex;
          align-items: center;
          gap: 6px;
          opacity: 0;
          transform: translateY(-4px);
          transition: opacity 0.25s, transform 0.25s;
        }
        .error-msg.visible {
          opacity: 1;
          transform: translateY(0);
        }
        .custom-check {
          width: 16px;
          height: 16px;
          border-radius: 4px;
          background: rgba(20, 20, 23, 0.7);
          appearance: none;
          cursor: pointer;
          position: relative;
          transition: all 0.2s;
          flex-shrink: 0;
          border: 1px solid var(--border-subtle);
        }
        .custom-check:checked {
          background: var(--accent);
          border-color: var(--accent);
        }
        .custom-check:checked::after {
          content: "";
          position: absolute;
          top: 2px;
          left: 5px;
          width: 4px;
          height: 8px;
          border: solid #000;
          border-width: 0 2px 2px 0;
          transform: rotate(45deg);
        }
        .custom-check:focus-visible {
          outline: 2px solid rgba(245, 158, 11, 0.4);
          outline-offset: 2px;
        }
        .pw-toggle {
          position: absolute;
          right: 14px;
          top: 50%;
          transform: translateY(-50%);
          background: none;
          border: none;
          color: var(--text-muted);
          cursor: pointer;
          padding: 4px;
          font-size: 14px;
          transition: color 0.2s;
        }
        .pw-toggle:hover {
          color: var(--text-primary);
        }
        .shake {
          animation: shake 0.4s ease;
        }
        @keyframes shake {
          0%,
          100% {
            transform: translateX(0);
          }
          20% {
            transform: translateX(-6px);
          }
          40% {
            transform: translateX(6px);
          }
          60% {
            transform: translateX(-4px);
          }
          80% {
            transform: translateX(4px);
          }
        }
        .mobile-brand {
          position: absolute;
          top: 1.5rem;
          left: 1.5rem;
          display: flex;
          align-items: center;
          gap: 0.625rem;
        }
        @media (min-width: 768px) {
          .mobile-brand {
            display: none !important;
          }
        }
      `}</style>

      <div className="bg-grid" />
      <div className="scan-line" />

      <div className="relative z-10 flex min-h-dvh w-full">
        <div className="left-panel hidden md:flex">
          <div className="glow-orb glow-orb-1" />
          <div className="glow-orb glow-orb-2" />
          <div className="glow-orb glow-orb-3" />

          <div className="relative z-10 fade-up">
            <div className="mb-3 flex items-center gap-3">
              <Image
                src="/logo.png"
                alt="Aether OpsCenter"
                width={40}
                height={40}
                priority
                unoptimized
                className="h-10 w-10 rounded-xl border border-amber-500/20 bg-amber-500/10 p-1"
              />
              <span className="text-lg font-semibold tracking-tight">Aether</span>
            </div>
            <p className="text-[10px] font-mono text-zinc-600 tracking-widest uppercase">
              © 2026 Aether OpsCenter. Internal use only.
            </p>
          </div>

          <div className="relative z-10 max-w-md fade-up delay-2">
              <h2 className="text-3xl lg:text-4xl font-bold leading-tight tracking-tight mb-5 text-[#fafafa]">
              Operational
              <br />
              <span style={{ color: "var(--accent)" }}>Intelligence</span>
              <br />
              at scale.
            </h2>
            <p className="text-sm text-zinc-500 leading-relaxed">
              Unified ticket management, incident response, and service monitoring backed by the
              live API used across the command center, reports, and replay views.
            </p>
          </div>

          <div className="relative z-10 space-y-4 fade-up delay-4">
            <div className="flex items-center gap-3">
              <div className="status-dot w-2 h-2 rounded-full bg-emerald-500" />
              <span className="text-[10px] font-mono text-emerald-400 tracking-wider uppercase">
                API-backed access
              </span>
            </div>

            <div className="grid gap-3">
              <div className="rounded-2xl border border-white/10 bg-black/20 p-4 backdrop-blur-sm">
                <div className="text-[10px] font-mono uppercase tracking-widest text-zinc-600">
                  Live workspace
                </div>
                <p className="mt-2 text-sm leading-6 text-zinc-400">
                  Sign in to open the current ticket queue, incident clusters, reports, and replay history.
                </p>
              </div>
              <div className="rounded-2xl border border-white/10 bg-black/20 p-4 backdrop-blur-sm">
                <div className="text-[10px] font-mono uppercase tracking-widest text-zinc-600">
                  Real authentication
                </div>
                <p className="mt-2 text-sm leading-6 text-zinc-400">
                  Sessions are stored in the browser after the backend issues a token.
                </p>
              </div>
              <div className="rounded-2xl border border-white/10 bg-black/20 p-4 backdrop-blur-sm">
                <div className="text-[10px] font-mono uppercase tracking-widest text-zinc-600">
                  Actionable routes
                </div>
                <p className="mt-2 text-sm leading-6 text-zinc-400">
                  Every route on the dashboard should lead to a real record, export, or review flow.
                </p>
              </div>
            </div>
          </div>
        </div>

        <div className="right-panel">
          <div className="mobile-brand fade-up">
            <Image
              src="/logo.png"
              alt="Aether"
              width={32}
              height={32}
              priority
              unoptimized
              className="h-8 w-8 rounded-lg border border-amber-500/20 bg-amber-500/10 p-1"
            />
            <span className="text-sm font-semibold">Aether</span>
          </div>

          <div className="w-full max-w-sm">
            <div className="flex items-center gap-2 mb-8 fade-up delay-1 md:hidden">
              <div className="status-dot w-1.5 h-1.5 rounded-full bg-emerald-500" />
              <span className="text-[10px] font-mono text-emerald-400">API-backed access</span>
            </div>

            <div className="mb-8 fade-up delay-1">
              <h1 className="text-2xl font-bold tracking-tight mb-1.5">{greeting}</h1>
              <p className="text-sm text-zinc-500">Sign in to your OpsCenter account</p>
            </div>

            {process.env.NODE_ENV !== "production" ? (
              <div
                className="fade-up delay-1 mb-6 flex items-center justify-between gap-3 rounded-2xl border border-amber-500/20 bg-amber-500/[0.06] px-4 py-3 text-[11px] text-amber-100/80"
                data-testid="demo-credentials"
              >
                <div className="flex items-center gap-2">
                  <span className="inline-block h-1.5 w-1.5 rounded-full bg-amber-400" aria-hidden="true" />
                  <span className="font-mono uppercase tracking-[0.18em] text-amber-200">Demo</span>
                </div>
                <div className="flex items-center gap-3 font-mono">
                  <span>
                    user <span className="text-amber-50">admin</span>
                  </span>
                  <span className="text-amber-400/60">/</span>
                  <span>
                    pass <span className="text-amber-50">admin123</span>
                  </span>
                </div>
                <button
                  type="button"
                  onClick={() => {
                    setUsername("admin");
                    setPassword("admin123");
                    clearErrors();
                  }}
                  className="rounded-full border border-amber-400/30 bg-amber-500/10 px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.16em] text-amber-100 transition hover:bg-amber-500/20"
                >
                  Fill
                </button>
              </div>
            ) : null}

            <form
              id="login-form"
              onSubmit={handleSubmit}
              className="space-y-4"
              noValidate
            >
              <div className="fade-up delay-2">
                <label
                  htmlFor="username"
                  className="block text-[10px] font-mono text-zinc-500 uppercase tracking-widest mb-2"
                >
                  Username
                </label>
                <div className="relative">
                  <User className="absolute left-4 top-1/2 -translate-y-1/2 text-zinc-600 text-xs w-4 h-4" />
                  <input
                    type="text"
                    id="username"
                    name="username"
                    value={username}
                    onChange={(e) => {
                      setUsername(e.target.value);
                      if (errors.username) clearErrors();
                    }}
                    className={`form-input ${errors.username ? "error" : ""}`}
                    placeholder="Enter your username"
                    autoComplete="username"
                    aria-label="Username"
                    required
                    spellCheck={false}
                    autoCapitalize="off"
                  />
                </div>
                <div
                  id="username-error"
                  className={`error-msg ${errors.username ? "visible" : ""}`}
                >
                  <AlertCircle className="text-[10px] w-3 h-3" />
                  <span>{errors.username}</span>
                </div>
              </div>

              <div className="fade-up delay-3">
                <label
                  htmlFor="password"
                  className="block text-[10px] font-mono text-zinc-500 uppercase tracking-widest mb-2"
                >
                  Password
                </label>
                <div className="relative">
                  <Lock className="absolute left-4 top-1/2 -translate-y-1/2 text-zinc-600 text-xs w-4 h-4" />
                  <input
                    type={showPassword ? "text" : "password"}
                    id="password"
                    name="password"
                    value={password}
                    onChange={(e) => {
                      setPassword(e.target.value);
                      if (errors.password) clearErrors();
                    }}
                    className={`form-input ${errors.password ? "error" : ""}`}
                    placeholder="Enter your password"
                    aria-label="Password"
                    required
                    style={{ paddingRight: "44px" }}
                  />
                  <button
                    type="button"
                    id="pw-toggle"
                    className="pw-toggle"
                    onClick={() => setShowPassword(!showPassword)}
                    aria-label="Toggle password visibility"
                  >
                    {showPassword ? (
                      <EyeOff className="w-4 h-4" />
                    ) : (
                      <Eye className="w-4 h-4" />
                    )}
                  </button>
                </div>
                <div
                  id="password-error"
                  className={`error-msg ${errors.password ? "visible" : ""}`}
                >
                  <AlertCircle className="text-[10px] w-3 h-3" />
                  <span>{errors.password}</span>
                </div>
              </div>

              <div className="flex items-center justify-between fade-up delay-4">
                <label className="flex items-center gap-2.5 cursor-pointer select-none">
                  <input
                    type="checkbox"
                    id="remember"
                    className="custom-check"
                    aria-label="Remember this device"
                  />
                  <span className="text-[12px] text-zinc-500">Remember device</span>
                </label>
                <span className="text-[12px] text-zinc-600">Password resets are handled by your administrator.</span>
              </div>

                <div
                  id="general-error"
                  className={`error-msg ${errors.general ? "visible" : ""}`}
                  style={{ justifyContent: "center" }}
                >
                  <AlertCircle className="text-[10px] w-3 h-3" />
                  <span>{errors.general}</span>
                </div>

              <div className="fade-up delay-5 pt-1">
                <button
                  type="submit"
                  className="btn-submit"
                  disabled={isSubmitting}
                >
                  <span className="btn-shimmer" />
                  <span id="btn-text">
                    {isSubmitting ? (
                      <>
                        <Loader2 className="inline w-4 h-4 mr-2 animate-spin" />
                        Authenticating...
                      </>
                    ) : (
                      "Sign In"
                    )}
                  </span>
                </button>
              </div>
            </form>

            <div className="mt-10 text-center fade-up delay-6">
              <p className="text-[11px] text-zinc-700">
                Secured with TLS 1.3. JWT access tokens expire after 8 hours.
              </p>
              <p className="text-[10px] text-zinc-800 mt-2">
                © 2026 Wallner Expac, Inc. - Internal Use Only
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
