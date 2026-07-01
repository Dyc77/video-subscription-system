"use client"

import { SettingsPanel } from "@/components/dashboard/settings-panel"
import { DashboardShell } from "@/components/dashboard/dashboard-shell"

export default function SettingsPage() {
  return (
    <DashboardShell activeTab="settings">
      <SettingsPanel />
    </DashboardShell>
  )
}
