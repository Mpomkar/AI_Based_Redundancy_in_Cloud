import { useEffect } from "react";

export type ToastKind = "info" | "success" | "warn" | "error";

const FLASH_KEY = "cr_flash_toast";

export type FlashToast = {
  message: string;
  kind: ToastKind;
};

type Props = {
  message: string | null;
  kind?: ToastKind;
  onClose: () => void;
  durationMs?: number;
};

const ICONS: Record<ToastKind, string> = {
  success: "✓",
  warn: "!",
  error: "✕",
  info: "i",
};

export default function Toast({
  message,
  kind = "info",
  onClose,
  durationMs = 5000,
}: Props) {
  useEffect(() => {
    if (!message) return;
    const t = window.setTimeout(onClose, durationMs);
    return () => window.clearTimeout(t);
  }, [message, durationMs, onClose]);

  if (!message) return null;

  return (
    <div className={`app-toast app-toast-${kind}`} role="status" aria-live="polite">
      <span className="app-toast-icon" aria-hidden>
        {ICONS[kind]}
      </span>
      <span className="app-toast-text">{message}</span>
      <button
        type="button"
        className="app-toast-close"
        onClick={onClose}
        aria-label="Close"
      >
        ×
      </button>
    </div>
  );
}

export function toastKindFromDecision(decision: string): ToastKind {
  if (decision === "stored_shared") return "warn";
  if (decision === "stored") return "success";
  if (decision === "rejected_duplicate" || decision === "rejected_redundant")
    return "error";
  return "info";
}

/** Persist a toast across navigation (login / logout). */
export function setFlashToast(message: string, kind: ToastKind = "info"): void {
  try {
    sessionStorage.setItem(FLASH_KEY, JSON.stringify({ message, kind } satisfies FlashToast));
  } catch {
    /* ignore */
  }
}

/** Read and clear a flash toast (call once on page mount). */
export function consumeFlashToast(): FlashToast | null {
  try {
    const raw = sessionStorage.getItem(FLASH_KEY);
    if (!raw) return null;
    sessionStorage.removeItem(FLASH_KEY);
    return JSON.parse(raw) as FlashToast;
  } catch {
    return null;
  }
}
