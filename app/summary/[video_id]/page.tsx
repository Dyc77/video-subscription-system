"use client"

import { use } from "react"
import { VideoSummary } from "@/components/dashboard/video-summary"
import { DashboardShell } from "@/components/dashboard/dashboard-shell"

export default function SummaryPage({ params }: { params: Promise<{ video_id: string }> }) {
  const { video_id } = use(params)

  return (
    <DashboardShell activeTab="summary">
      <VideoSummary videoId={video_id} />
    </DashboardShell>
  )
}
