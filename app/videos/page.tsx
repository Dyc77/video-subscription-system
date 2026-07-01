"use client"

import { useRouter } from "next/navigation"
import { VideoList } from "@/components/dashboard/video-list"
import { DashboardShell } from "@/components/dashboard/dashboard-shell"

export default function VideosPage() {
  const router = useRouter()

  const handleVideoSelect = (videoId: string) => {
    router.push(`/summary/${videoId}`)
  }

  return (
    <DashboardShell activeTab="videos">
      <VideoList onVideoSelect={handleVideoSelect} />
    </DashboardShell>
  )
}
