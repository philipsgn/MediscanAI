import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { QueryProvider } from "@/components/QueryProvider";
import "./globals.css";
import { MedicalDisclaimerModal } from "@/components/common/MedicalDisclaimerModal";
import { ToastContainer } from "@/components/common/Toast";

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
        <body className="min-h-full flex flex-col bg-gray-50 font-[var(--font-inter)]">
          {/* Medical Disclaimer Gate — Bắt buộc đồng ý trước khi sử dụng */}
          <MedicalDisclaimerModal />
          {/* Toast notification layer */}
          <ToastContainer />
          {children}
        </body>
      </html>
    </QueryProvider>
  );
}
