"use client"

import { useEffect } from "react"
import { useRouter } from "next/navigation"
import Swal from "sweetalert2"
import { HeaderNavbar } from "./header-navbar"
import { isTokenExpired } from "@/lib/api"

export type TabType = "subscriptions" | "videos" | "summary" | "settings"

interface DashboardShellProps {
  children: React.ReactNode
  activeTab: TabType
}

export function DashboardShell({ children, activeTab }: DashboardShellProps) {
  const router = useRouter()

  useEffect(() => {
    // 檢查初始 Token 狀態
    if (isTokenExpired()) {
      Swal.fire({
        icon: 'warning',
        title: '登入已過期',
        text: '請重新登入以繼續使用',
        confirmButtonText: '確定',
        allowOutsideClick: false,
        allowEscapeKey: false
      }).then(() => {
        router.push('/')
      })
      return
    }

    // 監聽 token-expired 事件（由 API 層觸發）
    const handleTokenExpired = () => {
      Swal.fire({
        icon: 'warning',
        title: '登入已過期',
        text: '您的登入狀態已失效,請重新登入',
        confirmButtonText: '前往登入',
        allowOutsideClick: false,
        allowEscapeKey: false
      }).then(() => {
        router.push('/')
      })
    }

    window.addEventListener('token-expired', handleTokenExpired)

    return () => {
      window.removeEventListener('token-expired', handleTokenExpired)
    }
  }, [router])

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <HeaderNavbar activeTab={activeTab} />
      <main className="flex-1 overflow-auto w-full">
        {children}
      </main>
    </div>
  )
}
