"use client"

import { useEffect } from "react"
import { useRouter } from "next/navigation"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { GoogleLoginButton } from "@/components/google-login-button"
import { Play } from "lucide-react"
import { isTokenExpired } from "@/lib/api"

export function LoginPage() {
  const router = useRouter()

  useEffect(() => {
    // 檢查是否已登入，如果已登入則重定向到 dashboard
    if (!isTokenExpired()) {
      router.replace("/videos")
    }
  }, [router])

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <Card className="w-full max-w-md border-2 border-primary/30 bg-card">
        <CardHeader className="text-center space-y-4">
          <div className="mx-auto w-16 h-16 rounded-2xl bg-primary/10 border border-primary/30 flex items-center justify-center">
            <Play className="w-8 h-8 text-primary" />
          </div>
          <CardTitle className="text-2xl font-bold text-foreground">影片訂閱管理系統</CardTitle>
          <CardDescription className="text-muted-foreground">
            登入以管理您的影片訂閱
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <GoogleLoginButton />
        </CardContent>
      </Card>
    </div>
  )
}
