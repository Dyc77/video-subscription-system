"use client"

import { useState, useEffect } from "react"
import { useRouter, useSearchParams } from "next/navigation"
import Swal from "sweetalert2"
import { HeaderNavbar } from "./header-navbar"
import { SubscriptionManager } from "./subscription-manager"
import { VideoList } from "./video-list"
import { VideoSummary } from "./video-summary"
import { SettingsPanel } from "./settings-panel"
import { isTokenExpired } from "@/lib/api"

export type TabType = "subscriptions" | "videos" | "summary" | "settings"

export function DashboardLayout() {
  const router = useRouter()
  const searchParams = useSearchParams()

  // 從 URL 讀取 tab 和 video_id
  const urlTab = searchParams.get('tab') as TabType | null
  const urlVideoId = searchParams.get('video_id')

  const [activeTab, setActiveTab] = useState<TabType>(urlTab || "videos")
  const [selectedVideoId, setSelectedVideoId] = useState<string | null>(urlVideoId)


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

  // 同步 URL 參數與 state
  useEffect(() => {
    if (urlTab && urlTab !== activeTab) {
      setActiveTab(urlTab)
    }
    if (urlVideoId && urlVideoId !== selectedVideoId) {
      setSelectedVideoId(urlVideoId)
    }
  }, [urlTab, urlVideoId])

  const handleVideoSelect = (videoId: string) => {
    setSelectedVideoId(videoId)
    setActiveTab("summary")
    // 更新 URL，讓瀏覽器歷史記錄可以正確返回
    router.push(`/dashboard?tab=summary&video_id=${videoId}`)
  }

  const handleTabChange = (tab: TabType) => {
    setActiveTab(tab)
    // 更新 URL
    router.push(`/dashboard?tab=${tab}`)
  }

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <HeaderNavbar
        activeTab={activeTab}
        onTabChange={handleTabChange}
      />
      <main className="flex-1 overflow-auto w-full">
        {activeTab === "subscriptions" && <SubscriptionManager />}
        {activeTab === "videos" && <VideoList onVideoSelect={handleVideoSelect} />}
        {activeTab === "summary" && <VideoSummary videoId={selectedVideoId} />}
        {activeTab === "settings" && <SettingsPanel />}
      </main>
    </div>
  )
}
