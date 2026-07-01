"use client"

import { SubscriptionManager } from "@/components/dashboard/subscription-manager"
import { DashboardShell } from "@/components/dashboard/dashboard-shell"

export default function SubscriptionsPage() {
  return (
    <DashboardShell activeTab="subscriptions">
      <SubscriptionManager />
    </DashboardShell>
  )
}
