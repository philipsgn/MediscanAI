'use client';

/**
 * [P0/F4.10] QueryClientProvider wrapper — BẮT BUỘC là Client Component riêng.
 *
 * RootLayout trong Next.js App Router là Server Component; `@tanstack/react-query`
 * sử dụng React Context nên KHÔNG được khởi tạo trực tiếp trong layout (sẽ throw
 * "useContext must be called within a Client Component" khi next build).
 *
 * - `useState(() => new QueryClient(...))`: lazy initializer — tạo client ĐÚNG MỘT
 *   lần, tránh rò rỉ cache cross-request trong SSR/hydration.
 * - KHÔNG đặt `new QueryClient()` ở module scope (shared instance giữa requests
 *   gây cache mismatch giữa server-side render và client hydration).
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useState } from 'react';

export function QueryProvider({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: { staleTime: 30_000, retry: 1 },
          mutations: { retry: 1 },
        },
      })
  );
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
}