import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { QueryProvider } from "@/components/QueryProvider";
import "./globals.css";
import { MedicalDisclaimerModal } from "@/components/common/MedicalDisclaimerModal";
import { ToastContainer } from "@/components/common/Toast";
import { OnboardingGate } from "@/components/OnboardingGate";

const inter = Inter({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-inter",
});

export const metadata: Metadata = {
  title: "Mediscan AI — Trợ Lý Cảnh Báo Tương Tác Thuốc",
  description:
    "Mediscan AI giúp bạn nhận diện, chuẩn hóa và phân tích tương tác thuốc bằng mô hình OCR tự huấn luyện chạy on-premise. Hỗ trợ quét toa thuốc và vỏ hộp, cảnh báo nguy cơ trùng lặp hoạt chất và tương tác chéo.",
  keywords: "tương tác thuốc, kiểm tra thuốc, Mediscan AI, toa thuốc, an toàn thuốc",
};

import { ClinicalHeader } from "@/components/layout/ClinicalHeader";

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <QueryProvider>
      <html
        lang="vi"
        className={`${inter.variable} h-full antialiased`}
      >
        <body className="min-h-full flex flex-col bg-slate-50 font-[var(--font-inter)] text-slate-900 selection:bg-slate-900 selection:text-white">
          {/* Medical Disclaimer Gate — Bắt buộc đồng ý trước khi sử dụng */}
          <MedicalDisclaimerModal />
          {/* Toast notification layer */}
          <ToastContainer />
          {/* Onboarding Gate — redirect về /onboarding nếu chưa khai báo hồ sơ */}
          <OnboardingGate>
            <ClinicalHeader />
            <div className="flex-1 flex flex-col">
              {children}
            </div>
          </OnboardingGate>
        </body>
      </html>
    </QueryProvider>
  );
}

