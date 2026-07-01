"use client"

import { Button } from "@/components/ui/button"
import { Sheet, SheetContent } from "@/components/ui/sheet"
import { cn } from "@/lib/utils"
import { Play, Settings, Youtube, Rss, Menu } from "lucide-react"
import { UserAvatarMenu } from "./user-avatar-menu"
import type { TabType } from "./dashboard-layout"

interface SidebarProps {
  activeTab: TabType
  onTabChange: (tab: TabType) => void
  sidebarOpen: boolean
  setSidebarOpen: (open: boolean) => void
}

const navItems = [
  { id: "videos" as TabType, label: "影片列表", icon: Youtube },
  { id: "subscriptions" as TabType, label: "訂閱管理", icon: Rss },
  { id: "settings" as TabType, label: "設定", icon: Settings },
]

function SidebarContent({ activeTab, onTabChange }: {
  activeTab: TabType
  onTabChange: (tab: TabType) => void
}) {
  return (
    <>
      <div className="p-4 border-b border-sidebar-border">
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-primary/10 border border-primary/30 flex items-center justify-center">
              <Play className="w-5 h-5 text-primary" />
            </div>
            <div>
              <h1 className="font-semibold text-sidebar-foreground">VideoHub</h1>
              <p className="text-xs text-muted-foreground">訂閱管理系統</p>
            </div>
          </div>
          <UserAvatarMenu />
        </div>
      </div>

      <nav className="flex-1 p-4 space-y-2">
        {navItems.map((item) => (
          <Button
            key={item.id}
            variant="ghost"
            onClick={() => onTabChange(item.id)}
            className={cn(
              "w-full justify-start gap-3 h-11 text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
              activeTab === item.id && "bg-sidebar-accent border border-primary/30 text-primary",
            )}
          >
            <item.icon className="w-5 h-5" />
            {item.label}
          </Button>
        ))}
      </nav>
    </>
  )
}

export function Sidebar({ activeTab, onTabChange, sidebarOpen, setSidebarOpen }: SidebarProps) {
  return (
    <>
      {/* 移動端漢堡選單按鈕 */}
      <Button
        variant="ghost"
        size="icon"
        className="fixed top-4 right-4 z-50 lg:hidden bg-background border border-border shadow-md"
        onClick={() => setSidebarOpen(true)}
      >
        <Menu className="w-5 h-5" />
      </Button>

      {/* 桌面端側邊欄 */}
      <aside className="hidden lg:flex w-64 min-h-screen bg-sidebar border-r border-sidebar-border flex-col">
        <SidebarContent activeTab={activeTab} onTabChange={onTabChange} />
      </aside>

      {/* 移動端側邊欄（使用 Sheet） */}
      <Sheet open={sidebarOpen} onOpenChange={setSidebarOpen}>
        <SheetContent side="left" className="p-0 w-64 bg-sidebar border-r border-sidebar-border">
          <div className="flex flex-col h-full">
            <SidebarContent activeTab={activeTab} onTabChange={onTabChange} />
          </div>
        </SheetContent>
      </Sheet>
    </>
  )
}
