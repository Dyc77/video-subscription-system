"use client"

import { VideoSummary } from "@/components/dashboard/video-summary"
import { DashboardShell } from "@/components/dashboard/dashboard-shell"

export default function SummaryPage({ params }: { params: { video_id: string } }) {
  return (
    <DashboardShell activeTab="summary">
      <VideoSummary videoId={params.video_id} />
    </DashboardShell>
  )
}
