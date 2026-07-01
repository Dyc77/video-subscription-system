"use client"

import { useState } from "react"
import Link from "next/link"
import { Button } from "@/components/ui/button"
import { Sheet, SheetContent } from "@/components/ui/sheet"
import { cn } from "@/lib/utils"
import { Play, Settings, Youtube, Rss, Menu } from "lucide-react"
import { UserAvatarMenu } from "./user-avatar-menu"
import type { TabType } from "./dashboard-shell"

interface HeaderNavbarProps {
  activeTab: TabType
}

const navItems = [
  { id: "videos" as TabType, label: "影片列表", icon: Youtube, href: "/videos" },
  { id: "subscriptions" as TabType, label: "訂閱管理", icon: Rss, href: "/subscriptions" },
  { id: "settings" as TabType, label: "設定", icon: Settings, href: "/settings" },
]

export function HeaderNavbar({ activeTab }: HeaderNavbarProps) {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  return (
    <>
      {/* Header 導航欄 */}
      <header className="sticky top-0 z-40 w-full border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="flex h-16 items-center justify-between px-4 md:px-6">
          {/* Logo 區域 */}
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-primary/10 border border-primary/30 flex items-center justify-center">
              <Play className="w-5 h-5 text-primary" />
            </div>
            <div>
              <h1 className="font-semibold text-foreground">VideoHub</h1>
              <p className="text-xs text-muted-foreground hidden sm:block">訂閱管理系統</p>
            </div>
          </div>

          {/* 右側區域 */}
          <div className="flex items-center gap-2 ml-auto">
            {/* 桌面端導航選單 */}
            <nav className="hidden md:flex items-center gap-2">
              {navItems.map((item) => (
                <Link key={item.id} href={item.href}>
                  <Button
                    variant="ghost"
                    className={cn(
                      "gap-2 h-10 px-4 text-foreground hover:bg-accent hover:text-accent-foreground transition-colors",
                      activeTab === item.id && "bg-primary text-primary-foreground hover:bg-primary/90",
                    )}
                  >
                    <item.icon className="w-4 h-4" />
                    {item.label}
                  </Button>
                </Link>
              ))}
            </nav>
            {/* 用戶頭像選單（桌面端） */}
            <div className="hidden md:block">
              <UserAvatarMenu />
            </div>

            {/* 移動端漢堡選單按鈕 */}
            <Button
              variant="ghost"
              size="icon"
              className="md:hidden h-10 w-10"
              onClick={() => setMobileMenuOpen(true)}
            >
              <Menu className="w-5 h-5" />
            </Button>
          </div>
        </div>
      </header>

      {/* 移動端選單（Sheet） */}
      <Sheet open={mobileMenuOpen} onOpenChange={setMobileMenuOpen}>
        <SheetContent side="right" className="w-72 p-0">
          <div className="flex flex-col h-full">
            {/* 選單標題 */}
            <div className="p-4 border-b border-border flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-primary/10 border border-primary/30 flex items-center justify-center">
                <Play className="w-5 h-5 text-primary" />
              </div>
              <div>
                <h2 className="font-semibold text-foreground">選單</h2>
                <p className="text-xs text-muted-foreground">VideoHub</p>
              </div>
            </div>

            {/* 導航選項 */}
            <nav className="flex-1 p-4 space-y-2">
              {navItems.map((item) => (
                <Link key={item.id} href={item.href} onClick={() => setMobileMenuOpen(false)}>
                  <Button
                    variant="ghost"
                    className={cn(
                      "w-full justify-start gap-3 h-12 text-foreground hover:bg-accent hover:text-accent-foreground",
                      activeTab === item.id && "bg-primary text-primary-foreground hover:bg-primary/90",
                    )}
                  >
                    <item.icon className="w-5 h-5" />
                    <span className="text-base">{item.label}</span>
                  </Button>
                </Link>
              ))}
            </nav>

            {/* 底部用戶資訊 */}
            <div className="p-4 border-t border-border">
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground"></span>
                <UserAvatarMenu />
              </div>
            </div>
          </div>
        </SheetContent>
      </Sheet>
    </>
  )
}
