"use client"

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Switch } from "@/components/ui/switch"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Separator } from "@/components/ui/separator"
import { Bell, Mail, Smartphone, Clock, Type, Trash2, AlertTriangle, Palette, Save } from "lucide-react"
import Swal from "sweetalert2"
import { getUserSetting, updateUserSetting, UserSetting, generateLineBindingToken, getLineBindingStatus, unbindLine, LineBindingStatus } from "@/lib/api"
import { useToast } from "@/hooks/use-toast"
import { Link as LinkIcon, CheckCircle2 } from "lucide-react"

// AI 設定選項（寫死在前端）
const AI_TONES = [
  { value: "professional", label: "專業" },
  { value: "humorous", label: "幽默" },
  { value: "friendly", label: "親切" },
  { value: "concise", label: "簡潔" },
  { value: "critical", label: "批判" },
  { value: "encouraging", label: "鼓勵" },
]

const AI_PERSONAS = [
  { value: "general", label: "一般助理" },
  { value: "engineer", label: "工程師" },
  { value: "teacher", label: "老師" },
  { value: "investor", label: "投資者" },
  { value: "critic", label: "影評人" },
  { value: "summarizer", label: "摘要員" },
]

const SUMMARY_LENGTHS = [
  { value: 100, label: "100字" },
  { value: 200, label: "200字" },
  { value: 300, label: "300字" },
  { value: 500, label: "500字" },
  { value: 800, label: "800字" },
  { value: 1000, label: "1000字" },
]

const NOTIFY_INTERVALS = [
  { value: 30, label: "30 分鐘" },
  { value: 60, label: "1 小時" },
  { value: 120, label: "2 小時" },
  { value: 240, label: "4 小時" },
  { value: 360, label: "6 小時" },
  { value: 720, label: "12 小時" },
  { value: 1440, label: "1 天" },
]

export function SettingsPanel() {
  const { toast } = useToast()

  const [settings, setSettings] = useState<UserSetting | null>(null)
  const [savedSettings, setSavedSettings] = useState<UserSetting | null>(null)
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false)

  // LINE 綁定相關狀態
  const [lineBindingStatus, setLineBindingStatus] = useState<LineBindingStatus | null>(null)
  const [isGeneratingToken, setIsGeneratingToken] = useState(false)

  // 載入使用者設定
  useEffect(() => {
    loadSettings()
    loadLineBindingStatus()
  }, [])

  const loadSettings = async () => {
    try {
      const userSettings = await getUserSetting()
      setSettings(userSettings)
      setSavedSettings(userSettings)
    } catch (error) {
      console.error("載入設定失敗:", error)
      toast({
        title: "載入失敗",
        description: "無法載入設定，請重新整理頁面",
        variant: "destructive",
      })
    }
  }

  const loadLineBindingStatus = async () => {
    try {
      const status = await getLineBindingStatus()
      setLineBindingStatus(status)
    } catch (error) {
      console.error("載入 LINE 綁定狀態失敗:", error)
    }
  }

  const handleBindLine = async () => {
    setIsGeneratingToken(true)
    try {
      const result = await generateLineBindingToken()

      // 檢測是否為手機裝置
      const isMobile = /iPhone|iPad|iPod|Android/i.test(navigator.userAgent)

      if (isMobile) {
        // 手機版：直接顯示確認對話框，點擊後開啟 LINE
        const htmlContent = `
          <div style="text-align: left;">
            <p style="margin-bottom: 15px; font-size: 14px;">請按照以下步驟完成綁定：</p>
            <ol style="text-align: left; padding-left: 20px; margin-bottom: 20px;">
              ${result.instructions.map(instruction => `<li style="margin-bottom: 8px;">${instruction}</li>`).join('')}
            </ol>
            <div style="background: #f3f4f6; padding: 15px; border-radius: 8px; margin-bottom: 15px;">
              <p style="font-size: 12px; color: #6b7280; margin-bottom: 8px;">您的綁定碼（有效期 10 分鐘）：</p>
              <p style="font-size: 18px; font-weight: bold; font-family: monospace; color: #3b82f6;">${result.token}</p>
            </div>
            <p style="font-size: 12px; color: #6b7280;">💡 提示：點擊按鈕後會自動開啟 LINE 並填入驗證碼</p>
          </div>
        `

        const dialogResult = await Swal.fire({
          icon: "info",
          title: "📱 開啟 LINE 完成綁定",
          html: htmlContent,
          showCancelButton: true,
          confirmButtonText: "開啟 LINE",
          cancelButtonText: "稍後再說",
          confirmButtonColor: "#06C755",
          width: "500px",
        })

        if (dialogResult.isConfirmed) {
          // 開啟 LINE Deep Link
          window.location.href = result.deep_link

          toast({
            title: "已開啟 LINE",
            description: "請在 LINE 中按下傳送完成綁定",
          })
        }
      } else {
        // 電腦版：顯示綁定碼和 QR Code 說明
        const htmlContent = `
          <div style="text-align: center;">
            <div style="background: #f3f4f6; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
              <p style="font-size: 14px; color: #374151; margin-bottom: 12px; font-weight: 500;">📱 您的綁定碼</p>
              <div style="background: white; padding: 15px; border-radius: 6px; border: 2px solid #3b82f6;">
                <p style="font-size: 32px; font-weight: bold; font-family: monospace; color: #3b82f6; letter-spacing: 3px;">${result.token}</p>
              </div>
              <p style="font-size: 12px; color: #6b7280; margin-top: 8px;">⏰ 有效期限：10 分鐘</p>
            </div>

            <div style="text-align: left; background: #ecfdf5; padding: 15px; border-radius: 8px; border-left: 4px solid #10b981;">
              <p style="font-size: 13px; color: #065f46; margin-bottom: 10px; font-weight: 600;">📝 綁定步驟：</p>
              <ol style="text-align: left; padding-left: 20px; margin: 0; color: #047857; font-size: 13px; line-height: 1.8;">
                <li>在手機上開啟 LINE App</li>
                <li>前往 VideoHub 官方帳號聊天室</li>
                <li>手動輸入上方綁定碼並傳送</li>
                <li>等待綁定成功通知</li>
              </ol>
            </div>

            <div style="margin-top: 15px; padding: 12px; background: #fef3c7; border-radius: 6px;">
              <p style="font-size: 12px; color: #92400e; margin: 0;">
                💡 提示：請使用手機 LINE App 輸入綁定碼
              </p>
            </div>
          </div>
        `

        await Swal.fire({
          icon: "info",
          title: "📱 請在 LINE 中輸入綁定碼",
          html: htmlContent,
          confirmButtonText: "我知道了",
          confirmButtonColor: "#06C755",
          width: "550px",
          customClass: {
            popup: 'binding-code-popup'
          }
        })

        toast({
          title: "綁定碼已生成",
          description: "請在手機 LINE 中輸入綁定碼完成綁定",
          duration: 5000,
        })
      }

      // 每 3 秒檢查一次綁定狀態，最多檢查 10 次（30 秒）
      let checkCount = 0
      const maxChecks = 10
      const checkInterval = setInterval(async () => {
        checkCount++
        const status = await getLineBindingStatus()

        if (status.is_bound) {
          // 綁定成功！
          setLineBindingStatus(status)
          clearInterval(checkInterval)

          // 自動開啟 LINE 通知
          if (settings && settings.enable_line === 0) {
            updateSetting('enable_line', 1)
            // 立即儲存設定
            await updateUserSetting({ enable_line: 1 })
          }

          // 顯示成功訊息
          Swal.fire({
            icon: "success",
            title: "綁定成功！",
            text: "已自動開啟 LINE 通知功能",
            confirmButtonText: "確定",
            confirmButtonColor: "#06C755",
          })
        } else if (checkCount >= maxChecks) {
          // 超過最大檢查次數
          clearInterval(checkInterval)
        }
      }, 3000)

    } catch (error) {
      console.error("生成綁定連結失敗:", error)
      Swal.fire({
        icon: "error",
        title: "綁定失敗",
        text: "無法生成綁定連結，請稍後再試",
        confirmButtonText: "確定",
      })
    } finally {
      setIsGeneratingToken(false)
    }
  }

  const handleUnbindLine = async () => {
    const result = await Swal.fire({
      icon: "warning",
      title: "確定要解除綁定？",
      text: "解除後將無法收到 LINE 通知",
      showCancelButton: true,
      confirmButtonText: "確定解除",
      cancelButtonText: "取消",
      confirmButtonColor: "#dc2626",
    })

    if (result.isConfirmed) {
      try {
        await unbindLine()
        await loadLineBindingStatus()

        Swal.fire({
          icon: "success",
          title: "解除成功",
          text: "已解除 LINE 綁定",
          confirmButtonText: "確定",
        })
      } catch (error) {
        console.error("解除綁定失敗:", error)
        Swal.fire({
          icon: "error",
          title: "解除失敗",
          text: "無法解除綁定，請稍後再試",
          confirmButtonText: "確定",
        })
      }
    }
  }

  // 更新設定的通用函數
  const updateSetting = <K extends keyof UserSetting>(key: K, value: UserSetting[K]) => {
    if (!settings) return
    setSettings({ ...settings, [key]: value })
    setHasUnsavedChanges(true)
  }

  const handleSaveSettings = async () => {
    if (!settings || !savedSettings) return

    try {
      // 準備更新資料（只更新有變更的欄位）
      const updates: Partial<Omit<UserSetting, 'user_no' | 'updated_at'>> = {}

      if (settings.notify_enable !== savedSettings.notify_enable) {
        updates.notify_enable = settings.notify_enable
      }
      if (settings.notify_interval !== savedSettings.notify_interval) {
        updates.notify_interval = settings.notify_interval
      }
      if (settings.enable_line !== savedSettings.enable_line) {
        updates.enable_line = settings.enable_line
      }
      if (settings.enable_email !== savedSettings.enable_email) {
        updates.enable_email = settings.enable_email
      }
      if (settings.ai_summary_length !== savedSettings.ai_summary_length) {
        updates.ai_summary_length = settings.ai_summary_length
      }
      if (settings.ai_tone !== savedSettings.ai_tone) {
        updates.ai_tone = settings.ai_tone
      }
      if (settings.ai_persona !== savedSettings.ai_persona) {
        updates.ai_persona = settings.ai_persona
      }

      // 呼叫 API 更新
      const updatedSettings = await updateUserSetting(updates)

      // 更新已儲存的狀態
      setSavedSettings(updatedSettings)
      setSettings(updatedSettings)
      setHasUnsavedChanges(false)

      // 顯示成功訊息
      Swal.fire({
        icon: "success",
        title: "儲存成功",
        text: "設定已更新！",
        confirmButtonText: "確定",
      })

      toast({
        title: "儲存成功",
        description: "您的設定已更新",
      })

    } catch (error) {
      console.error("儲存設定失敗:", error)
      Swal.fire({
        icon: "error",
        title: "儲存失敗",
        text: "無法儲存設定，請稍後再試",
        confirmButtonText: "確定",
      })
    }
  }

  const handleDeleteAccount = async () => {
    const result = await Swal.fire({
      icon: "warning",
      title: "確定要刪除帳號？",
      text: "此操作無法復原，您的所有資料將被永久刪除。",
      showCancelButton: true,
      confirmButtonText: "確定刪除",
      cancelButtonText: "取消",
      confirmButtonColor: "#dc2626",
      cancelButtonColor: "#6b7280",
    })

    if (result.isConfirmed) {
      // Delete account logic
      window.location.href = "/"
    }
  }

  if (!settings) {
    return (
      <div className="p-6 space-y-6 max-w-4xl">
        <div className="text-center py-4 text-muted-foreground">載入中...</div>
      </div>
    )
  }

  return (
    <div className="w-[90%] md:w-[80%] lg:w-[75%] mx-auto p-4 sm:p-6 space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-foreground">設定</h2>
        <p className="text-muted-foreground">配置您的偏好設定和通知</p>
      </div>

      {/* 使用 Grid 布局，在大螢幕上分兩欄 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

      {/* Notification Settings */}
      <Card className="border-border bg-card">
        <CardHeader>
          <div className="flex items-center gap-2">
            <Bell className="w-5 h-5 text-primary" />
            <CardTitle className="text-lg text-card-foreground">推薦通知</CardTitle>
          </div>
          <CardDescription>選擇您想要接收影片推薦的方式</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Mail className="w-4 h-4 text-muted-foreground" />
              <Label htmlFor="email-notif" className="text-foreground">
                Email 通知
              </Label>
            </div>
            <Switch
              id="email-notif"
              checked={settings.enable_email === 1}
              onCheckedChange={(checked) => updateSetting('enable_email', checked ? 1 : 0)}
            />
          </div>

          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Smartphone className="w-4 h-4 text-muted-foreground" />
              <Label htmlFor="line-notif" className="text-foreground">
                Line 通知
              </Label>
            </div>
            <Switch
              id="line-notif"
              checked={settings.enable_line === 1}
              onCheckedChange={(checked) => updateSetting('enable_line', checked ? 1 : 0)}
            />
          </div>

          <Separator className="bg-border" />

          {/* 步驟 1: 加入 LINE 官方帳號 */}
          <div className="space-y-3">
            <div>
              <Label className="text-foreground">步驟 1：加入 LINE 官方帳號</Label>
              <p className="text-sm text-muted-foreground">
                點擊下方按鈕直接開啟 LINE 加入好友（無需掃描 QR Code）
              </p>
            </div>

            <div className="p-4 bg-blue-50 border border-blue-200 rounded-md">
              <div className="flex flex-col items-center space-y-3">
                <p className="text-sm font-medium text-blue-900">📱 點擊按鈕加入好友</p>

                <Button
                  onClick={() => {
                    window.open('https://line.me/R/ti/p/@333wpdzm', '_blank')
                  }}
                  className="w-full max-w-xs bg-[#06C755] hover:bg-[#05B04B] text-white"
                >
                  <Smartphone className="w-4 h-4 mr-2" />
                  開啟 LINE 加入好友
                </Button>

                <div className="text-center space-y-1">
                  <p className="text-xs text-gray-600">
                    點擊按鈕後會開啟 LINE App<br />
                    請點擊「加入好友」完成第一步
                  </p>
                </div>
              </div>
            </div>
          </div>

          <Separator className="bg-border" />

          {/* 步驟 2: 綁定 LINE 帳號 */}
          <div className="space-y-4">
            <div>
              <Label className="text-foreground">步驟 2：綁定 LINE 帳號</Label>
              <p className="text-sm text-muted-foreground">
                完成加入好友後，點擊下方按鈕綁定您的帳號
              </p>
            </div>

            {lineBindingStatus?.is_bound ? (
              <div className="p-4 bg-green-50 border border-green-200 rounded-md">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <CheckCircle2 className="w-5 h-5 text-green-600" />
                    <div>
                      <p className="text-sm font-medium text-green-900">✅ 已綁定 LINE 帳號</p>
                      <p className="text-xs text-green-700 mt-1">您將收到訂閱頻道的新影片通知</p>
                    </div>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleUnbindLine}
                    className="border-red-300 text-red-700 hover:bg-red-50"
                  >
                    解除綁定
                  </Button>
                </div>
              </div>
            ) : (
              <div className="p-4 bg-amber-50 border border-amber-200 rounded-md">
                <div className="space-y-3">
                  <div className="flex items-center gap-2">
                    <AlertTriangle className="w-5 h-5 text-amber-600" />
                    <p className="text-sm font-medium text-amber-900">尚未綁定 LINE 帳號</p>
                  </div>
                  <p className="text-xs text-amber-700">
                    ⚠️ 請確認已完成步驟 1（加入 LINE 好友）後再進行綁定
                  </p>
                  <Button
                    onClick={handleBindLine}
                    disabled={isGeneratingToken}
                    className="w-full bg-[#06C755] hover:bg-[#05B04B] text-white"
                  >
                    <LinkIcon className="w-4 h-4 mr-2" />
                    {isGeneratingToken ? "生成中..." : "綁定 LINE 帳號"}
                  </Button>
                </div>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

        {/* Timing Settings */}
        <Card className="border-border bg-card">
          <CardHeader>
            <div className="flex items-center gap-2">
              <Clock className="w-5 h-5 text-accent" />
              <CardTitle className="text-lg text-card-foreground">通知時間設定</CardTitle>
            </div>
            <CardDescription>配置通知時間和頻率</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <Label htmlFor="notification-enabled" className="text-foreground">通知開關</Label>
                <p className="text-sm text-muted-foreground">啟用或停用定期通知</p>
              </div>
              <Switch
                id="notification-enabled"
                checked={settings.notify_enable === 1}
                onCheckedChange={(checked) => updateSetting('notify_enable', checked ? 1 : 0)}
              />
            </div>

            <Separator className="bg-border" />

            <div className="flex items-center justify-between">
              <div>
                <Label className="text-foreground">通知間隔時間</Label>
                <p className="text-sm text-muted-foreground">設定接收通知的頻率</p>
              </div>
              <Select
                value={String(settings.notify_interval)}
                onValueChange={(value) => updateSetting('notify_interval', parseInt(value))}
              >
                <SelectTrigger className="w-32 bg-input border-border">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {NOTIFY_INTERVALS.map(interval => (
                    <SelectItem key={interval.value} value={String(interval.value)}>
                      {interval.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </CardContent>
        </Card>

      </div>

      {/* Summary Format Settings */}
      {/* <Card className="border-border bg-card">
        <CardHeader>
          <div className="flex items-center gap-2">
            <Type className="w-5 h-5 text-primary" />
            <CardTitle className="text-lg text-card-foreground">摘要格式設定</CardTitle>
          </div>
          <CardDescription>自訂 AI 摘要的生成方式</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Type className="w-4 h-4 text-muted-foreground" />
              <Label className="text-foreground">摘要字數</Label>
            </div>
            <Select
              value={String(settings.ai_summary_length)}
              onValueChange={(value) => updateSetting('ai_summary_length', parseInt(value))}
            >
              <SelectTrigger className="w-40 bg-input border-border">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {SUMMARY_LENGTHS.map(length => (
                  <SelectItem key={length.value} value={String(length.value)}>
                    {length.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Palette className="w-4 h-4 text-muted-foreground" />
              <Label className="text-foreground">語氣</Label>
            </div>
            <Select
              value={settings.ai_tone}
              onValueChange={(value) => updateSetting('ai_tone', value)}
            >
              <SelectTrigger className="w-40 bg-input border-border">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {AI_TONES.map(tone => (
                  <SelectItem key={tone.value} value={tone.value}>
                    {tone.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Palette className="w-4 h-4 text-muted-foreground" />
              <Label className="text-foreground">角色</Label>
            </div>
            <Select
              value={settings.ai_persona}
              onValueChange={(value) => updateSetting('ai_persona', value)}
            >
              <SelectTrigger className="w-40 bg-input border-border">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {AI_PERSONAS.map(persona => (
                  <SelectItem key={persona.value} value={persona.value}>
                    {persona.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card> */}

      {/* Danger Zone - 單獨一欄 (暫時隱藏) */}
      {/* <Card className="border-destructive/50 bg-card">
        <CardHeader>
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-destructive" />
            <CardTitle className="text-lg text-destructive">請注意</CardTitle>
          </div>
          <CardDescription>帳號的不可逆操作</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium text-foreground">刪除帳號</p>
              <p className="text-sm text-muted-foreground">永久刪除您的帳號及所有資料</p>
            </div>
            <Button
              variant="destructive"
              onClick={handleDeleteAccount}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              <Trash2 className="w-4 h-4 mr-2" />
              刪除帳號
            </Button>
          </div>
        </CardContent>
      </Card> */}

      {/* Save Button */}
      <Button
        onClick={handleSaveSettings}
        className="w-full h-12 bg-primary text-primary-foreground hover:bg-primary/90"
        disabled={!hasUnsavedChanges}
      >
        <Save className="w-5 h-5 mr-2" />
        {hasUnsavedChanges ? "儲存設定" : "已儲存"}
      </Button>
    </div>
  )
}
