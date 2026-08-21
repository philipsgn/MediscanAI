'use client';

import { useState, useEffect } from 'react';
import { CheckCircle2, AlertTriangle, Info, X } from 'lucide-react';
import { cn } from '@/lib/utils';

type ToastType = 'success' | 'error' | 'warning' | 'info';

interface Toast {
  id: string;
  type: ToastType;
  message: string;
}

let toastHandlers: ((toast: Toast) => void)[] = [];

// Exported API to trigger toasts from anywhere
export const toast = {
  success: (message: string) => emitToast('success', message),
  error: (message: string) => emitToast('error', message),
  warning: (message: string) => emitToast('warning', message),
  info: (message: string) => emitToast('info', message),
};

function emitToast(type: ToastType, message: string) {
  const t: Toast = { id: crypto.randomUUID(), type, message };
  toastHandlers.forEach(h => h(t));
}

export function ToastContainer() {
  const [toasts, setToasts] = useState<Toast[]>([]);

  useEffect(() => {
    const handler = (t: Toast) => {
      setToasts(prev => [...prev, t]);
      setTimeout(() => {
        setToasts(prev => prev.filter(x => x.id !== t.id));
      }, 4000);
    };
    toastHandlers.push(handler);
    return () => { toastHandlers = toastHandlers.filter(h => h !== handler); };
  }, []);

  const dismiss = (id: string) => setToasts(prev => prev.filter(x => x.id !== id));

  if (toasts.length === 0) return null;

  return (
    <div className="fixed bottom-6 right-6 z-[200] flex flex-col gap-2 pointer-events-none">
      {toasts.map(t => (
        <div
          key={t.id}
          className={cn(
            'flex items-center gap-3 px-4 py-3 rounded-xl shadow-lg border max-w-sm w-full pointer-events-auto',
            'animate-in slide-in-from-right-4 duration-300',
            t.type === 'success' && 'bg-emerald-50 border-emerald-200 text-emerald-800',
            t.type === 'error' && 'bg-red-50 border-red-200 text-red-800',
            t.type === 'warning' && 'bg-amber-50 border-amber-200 text-amber-800',
            t.type === 'info' && 'bg-blue-50 border-blue-200 text-blue-800',
          )}
        >
          {t.type === 'success' && <CheckCircle2 size={18} className="text-emerald-600 shrink-0" />}
          {t.type === 'error' && <AlertTriangle size={18} className="text-red-600 shrink-0" />}
          {t.type === 'warning' && <AlertTriangle size={18} className="text-amber-600 shrink-0" />}
          {t.type === 'info' && <Info size={18} className="text-blue-600 shrink-0" />}
          <p className="text-sm font-medium flex-1 leading-snug">{t.message}</p>
          <button onClick={() => dismiss(t.id)} className="shrink-0 opacity-50 hover:opacity-100 transition-opacity">
            <X size={15} />
          </button>
        </div>
      ))}
    </div>
  );
}
