import { useCallback, useEffect, useState } from "react";
import {
  consumeFlashToast,
  type ToastKind,
} from "../components/Toast";

export function useToast() {
  const [toast, setToast] = useState<string | null>(null);
  const [toastKind, setToastKind] = useState<ToastKind>("info");

  const clearToast = useCallback(() => setToast(null), []);

  const showToast = useCallback((message: string, kind: ToastKind = "info") => {
    setToast(message);
    setToastKind(kind);
  }, []);

  useEffect(() => {
    const flash = consumeFlashToast();
    if (flash) showToast(flash.message, flash.kind);
  }, [showToast]);

  return { toast, toastKind, showToast, clearToast };
}
