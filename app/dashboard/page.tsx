"use client"

import { useEffect } from "react"
import { useRouter } from "next/navigation"

export default function DashboardPage() {
  const router = useRouter()

  useEffect(() => {
    // 重定向到影片列表
    router.replace("/videos")
  }, [router])

  return null
}
