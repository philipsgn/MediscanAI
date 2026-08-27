import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

/**
 * Next.js Middleware — Kiểm tra cookie xác thực cho các protected routes.
 */

// Các route bắt buộc phải đăng nhập mới được truy cập
const PROTECTED_ROUTES = ['/account', '/history', '/reminders'];
// Các route dành cho khách (chưa đăng nhập)
const AUTH_ROUTES = ['/login', '/register'];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const token = request.cookies.get('mediscan_auth_token')?.value;

  const isProtectedRoute = PROTECTED_ROUTES.some((route) => pathname.startsWith(route));
  const isAuthRoute = AUTH_ROUTES.some((route) => pathname.startsWith(route));

  // Nếu vào protected route mà chưa đăng nhập -> chuyển về /login
  if (isProtectedRoute && !token) {
    const loginUrl = new URL('/login', request.url);
    loginUrl.searchParams.set('redirect', pathname);
    return NextResponse.redirect(loginUrl);
  }

  // Nếu đã đăng nhập mà lại vào /login hoặc /register -> chuyển về /scan
  if (isAuthRoute && token) {
    return NextResponse.redirect(new URL('/scan', request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ['/account/:path*', '/history/:path*', '/reminders/:path*', '/login', '/register'],
};
