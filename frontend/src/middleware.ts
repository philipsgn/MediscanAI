import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

/**
 * Next.js Middleware — Strict User Lifecycle Routing (State Machine).
 * Chặn các truy cập chưa xác thực và điều hướng theo trạng thái session.
 */

const PUBLIC_AUTH_ROUTES = ['/login', '/register'];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const token = request.cookies.get('mediscan_auth_token')?.value;

  const isAuthRoute = PUBLIC_AUTH_ROUTES.some((route) => pathname.startsWith(route));

  // 1. Nếu chưa đăng nhập và cố vào bất kỳ route nào khác /login hoặc /register
  if (!token && !isAuthRoute) {
    const loginUrl = new URL('/login', request.url);
    if (pathname !== '/') {
      loginUrl.searchParams.set('redirect', pathname);
    }
    return NextResponse.redirect(loginUrl);
  }

  // 2. Nếu đã đăng nhập mà lại truy cập /login hoặc /register -> điều hướng tới /cabinet
  if (token && isAuthRoute) {
    return NextResponse.redirect(new URL('/cabinet', request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - api (API routes)
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     */
    '/((?!api|_next/static|_next/image|favicon.ico).*)',
  ],
};
