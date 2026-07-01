import type React from "react"
import type { Metadata, Viewport } from "next"
import { Geist, Geist_Mono } from "next/font/google"
import { Analytics } from "@vercel/analytics/next"
import { GoogleOAuthProvider } from '@react-oauth/google'
import { Toaster } from "@/components/ui/toaster"
import "./globals.css"

const _geist = Geist({ subsets: ["latin"] })
const _geistMono = Geist_Mono({ subsets: ["latin"] })

// <CHANGE> Updated metadata for video subscription app
export const metadata: Metadata = {
  title: "VideoHub - Subscription Manager",
  description: "Manage your YouTube subscriptions, discover new videos, and get AI-powered summaries",
  generator: "v0.app",
  icons: {
    icon: [
      {
        url: "/icon-light-32x32.png",
        media: "(prefers-color-scheme: light)",
      },
      {
        url: "/icon-dark-32x32.png",
        media: "(prefers-color-scheme: dark)",
      },
      {
        url: "/icon.svg",
        type: "image/svg+xml",
      },
    ],
    apple: "/apple-icon.png",
  },
}

export const viewport: Viewport = {
  themeColor: "#1a1f35",
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  const googleClientId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID || '';

  return (
    <html lang="en">
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: `
              // 防止 iOS Safari 手勢返回
              if (typeof window !== 'undefined') {
                window.addEventListener('load', function() {
                  // 禁用整個頁面的手勢返回
                  document.body.style.overscrollBehaviorX = 'none';

                  // 防止 touchstart 在邊緣時觸發返回
                  let touchStartX = 0;
                  document.addEventListener('touchstart', function(e) {
                    touchStartX = e.touches[0].clientX;
                  }, { passive: true });

                  document.addEventListener('touchmove', function(e) {
                    // 如果從左邊緣滑動,阻止事件
                    if (touchStartX < 20 && e.touches[0].clientX > touchStartX) {
                      e.preventDefault();
                    }
                  }, { passive: false });
                });
              }
            `,
          }}
        />
      </head>
      <body className={`font-sans antialiased`} style={{ overscrollBehaviorX: 'none' }}>
        <GoogleOAuthProvider clientId={googleClientId}>
          {children}
          <Toaster />
          <Analytics />
        </GoogleOAuthProvider>
      </body>
    </html>
  )
}
