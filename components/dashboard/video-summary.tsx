"use client"

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Textarea } from "@/components/ui/textarea"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { VisuallyHidden } from "@radix-ui/react-visually-hidden"
import { RefreshCw, Sparkles, Clock, Eye, AlertCircle, X, Download, FileText, Save } from "lucide-react"
import { generateSummary, getUserVideos, saveVideoNote } from "@/lib/api"
import { useToast } from "@/hooks/use-toast"
import ReactMarkdown from "react-markdown"

interface VideoSummaryProps {
  videoId?: string | null
}


const exampleSummary = `## Video Summary

### Key Points
- **Main Topic**: This video covers the fundamentals of building modern web applications
- **Technology Stack**: Next.js 15, React Server Components, TypeScript
- **Duration**: Approximately 25 minutes of content

### Detailed Breakdown

1. **Introduction (0:00 - 2:30)**
   - Overview of the project goals
   - Setting up the development environment

2. **Core Concepts (2:30 - 12:00)**
   - Understanding server components
   - Client vs server rendering patterns
   - Data fetching strategies

3. **Implementation (12:00 - 20:00)**
   - Building the main application layout
   - Creating reusable components
   - Styling with Tailwind CSS

4. **Conclusion (20:00 - 24:35)**
   - Best practices summary
   - Next steps and resources

### Key Takeaways
- Server components improve initial load performance
- Use client components only when interactivity is needed
- Proper data fetching patterns reduce complexity`


export function VideoSummary({ videoId }: VideoSummaryProps) {
  const [isGenerating, setIsGenerating] = useState(false)
  const [summary, setSummary] = useState<string>("")
  const [customNotes, setCustomNotes] = useState("")
  const [hasSummary, setHasSummary] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [showVideoModal, setShowVideoModal] = useState(false)
  const [videoStartTime, setVideoStartTime] = useState<number>(0)
  const [isLoading, setIsLoading] = useState(false)
  const [isSavingNotes, setIsSavingNotes] = useState(false)
  const { toast } = useToast()

  // 當 videoId 變更時，自動檢查並載入摘要和筆記
  useEffect(() => {
    const loadExistingSummary = async () => {
      if (!videoId) return

      setIsLoading(true)
      setError(null)

      try {
        // 獲取所有影片，找到當前影片
        const videos = await getUserVideos()
        const currentVideo = videos.find(v => v.video_id === videoId)

        if (currentVideo) {
          if (currentVideo.summary_status === 2 && currentVideo.summary_content) {
            // 已有摘要，直接顯示
            setSummary(currentVideo.summary_content)
            setHasSummary(true)
          } else if (currentVideo.summary_status === 1) {
            // 正在生成中
            setError("AI 正在分析中，請稍後重試...")
          } else {
            // 沒有摘要或生成失敗
            setHasSummary(false)
            setSummary("")
          }

          // 載入使用者筆記（如果有的話）
          // 注意：需要更新 VideoResponse 來包含 user_note
          if ((currentVideo as any).user_note) {
            setCustomNotes((currentVideo as any).user_note)
          } else {
            setCustomNotes("")
          }
        }
      } catch (err) {
        console.error("載入摘要失敗:", err)
        // 載入失敗不顯示錯誤，讓使用者可以嘗試生成
      } finally {
        setIsLoading(false)
      }
    }

    loadExistingSummary()
  }, [videoId])

  const handleGenerateSummary = async () => {
    if (!videoId) {
      toast({
        title: "錯誤",
        description: "請先選擇一個影片",
        variant: "destructive",
      })
      return
    }

    setIsGenerating(true)
    setError(null)

    try {
      const result = await generateSummary(videoId)

      // 根據摘要狀態處理不同情況
      if (result.summary_status === 2 && result.summary_content) {
        // 成功生成摘要
        setSummary(result.summary_content)
        setHasSummary(true)
        toast({
          title: "成功",
          description: "影片摘要已生成！",
        })
        setIsGenerating(false)
      } else if (result.summary_status === 1) {
        // 正在處理中，啟動輪詢
        toast({
          title: "處理中",
          description: result.message || "AI 正在分析影片，將自動更新結果",
        })
        // 啟動輪詢檢查狀態
        startPolling()
      } else if (result.summary_status === 3) {
        // 無法生成摘要（無字幕）
        setError(result.message || "此影片無法生成摘要")
        toast({
          title: "無法生成摘要",
          description: result.message || "此影片可能沒有字幕或字幕無法獲取",
          variant: "destructive",
        })
        setIsGenerating(false)
      }
    } catch (err: any) {
      console.error("生成摘要失敗:", err)
      setError(err.message || "生成摘要時發生錯誤")
      toast({
        title: "錯誤",
        description: err.message || "生成摘要失敗，請稍後再試",
        variant: "destructive",
      })
      setIsGenerating(false)
    }
  }

  // 輪詢檢查摘要生成狀態
  const startPolling = () => {
    const pollInterval = setInterval(async () => {
      if (!videoId) {
        clearInterval(pollInterval)
        return
      }

      try {
        const videos = await getUserVideos()
        const currentVideo = videos.find(v => v.video_id === videoId)

        if (currentVideo) {
          if (currentVideo.summary_status === 2 && currentVideo.summary_content) {
            // 生成完成
            setSummary(currentVideo.summary_content)
            setHasSummary(true)
            setIsGenerating(false)
            setError(null)
            toast({
              title: "成功",
              description: "影片摘要已生成！",
            })
            clearInterval(pollInterval)
          } else if (currentVideo.summary_status === 3) {
            // 生成失敗
            setError("影片摘要生成失敗")
            setIsGenerating(false)
            toast({
              title: "生成失敗",
              description: "影片摘要生成失敗，請稍後再試",
              variant: "destructive",
            })
            clearInterval(pollInterval)
          }
          // status === 1 繼續輪詢
        }
      } catch (err) {
        console.error("輪詢摘要狀態失敗:", err)
        // 不中斷輪詢，繼續嘗試
      }
    }, 5000) // 每 5 秒檢查一次

    // 設定最大輪詢時間 5 分鐘
    setTimeout(() => {
      clearInterval(pollInterval)
      if (isGenerating) {
        setIsGenerating(false)
        setError("生成摘要超時，請稍後手動重新整理查看結果")
      }
    }, 300000) // 5 分鐘後停止輪詢
  }


  // 儲存筆記
  const handleSaveNotes = async () => {
    if (!videoId) {
      toast({
        title: "錯誤",
        description: "請先選擇一個影片",
        variant: "destructive",
      })
      return
    }

    setIsSavingNotes(true)

    try {
      await saveVideoNote(videoId, customNotes)

      toast({
        title: "儲存成功",
        description: "筆記已儲存",
      })
    } catch (err: any) {
      console.error("儲存筆記失敗:", err)
      toast({
        title: "儲存失敗",
        description: err.message || "無法儲存筆記，請稍後再試",
        variant: "destructive",
      })
    } finally {
      setIsSavingNotes(false)
    }
  }

  // 處理時間戳記連結點擊
  const handleTimestampClick = (e: React.MouseEvent<HTMLAnchorElement>, href: string) => {
    // 檢查是否是 YouTube 時間戳記連結
    const timeMatch = href.match(/[?&]t=(\d+)s?/)
    if (timeMatch && videoId) {
      e.preventDefault()
      const seconds = parseInt(timeMatch[1])
      setVideoStartTime(seconds)
      setShowVideoModal(true)
    }
  }

  return (
    <div className="w-[90%] md:w-[80%] lg:w-[75%] mx-auto p-4 md:p-6 space-y-4 md:space-y-6">
      {/* 影片播放 Modal */}
      <Dialog open={showVideoModal} onOpenChange={setShowVideoModal}>
        <DialogContent className="!w-[70vw] !max-w-[70vw] sm:!max-w-[70vw] p-0">
          <VisuallyHidden>
            <DialogTitle>影片播放</DialogTitle>
          </VisuallyHidden>
          <div className="aspect-video w-full bg-black">
            {videoId && (
              <iframe
                width="100%"
                height="100%"
                src={`https://www.youtube.com/embed/${videoId}?start=${videoStartTime}&autoplay=1&rel=0&modestbranding=1`}
                title="YouTube video player"
                frameBorder="0"
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
                allowFullScreen
                className="w-full h-full"
              ></iframe>
            )}
          </div>
          <div className="p-4 flex justify-end bg-secondary/30">
            <Button variant="outline" onClick={() => setShowVideoModal(false)} size="sm">
              <X className="w-4 h-4 mr-2" />
              關閉
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <div>
          <h2 className="text-xl md:text-2xl font-bold text-foreground">影片摘要</h2>
          <p className="text-sm text-muted-foreground">AI 生成的摘要和筆記</p>
        </div>
      </div>

      {isLoading ? (
        <div className="flex flex-col items-center justify-center py-12 md:py-20 space-y-4 md:space-y-6">
          <div className="w-20 h-20 md:w-24 md:h-24 rounded-full bg-primary/10 flex items-center justify-center">
            <RefreshCw className="w-10 h-10 md:w-12 md:h-12 text-primary animate-spin" />
          </div>
          <div className="text-center space-y-2 px-4">
            <h3 className="text-lg md:text-xl font-semibold text-foreground">載入摘要中...</h3>
            <p className="text-sm text-muted-foreground">正在檢查影片摘要狀態</p>
          </div>
        </div>
      ) : !hasSummary && !isGenerating ? (
        <div className="flex flex-col items-center justify-center py-12 md:py-20 space-y-4 md:space-y-6">
          {error ? (
            <>
              <div className="w-20 h-20 md:w-24 md:h-24 rounded-full bg-destructive/10 flex items-center justify-center">
                <AlertCircle className="w-10 h-10 md:w-12 md:h-12 text-destructive" />
              </div>
              <div className="text-center space-y-2 px-4">
                <h3 className="text-lg md:text-xl font-semibold text-foreground">生成失敗</h3>
                <p className="text-sm text-muted-foreground max-w-md">{error}</p>
              </div>
              <Button
                onClick={handleGenerateSummary}
                size="lg"
                variant="outline"
                className="h-11 md:h-12 px-6 md:px-8"
              >
                <RefreshCw className="w-4 h-4 md:w-5 md:h-5 mr-2" />
                重試
              </Button>
            </>
          ) : (
            <>
              <div className="w-20 h-20 md:w-24 md:h-24 rounded-full bg-muted/30 flex items-center justify-center">
                <Sparkles className="w-10 h-10 md:w-12 md:h-12 text-muted-foreground" />
              </div>
              <div className="text-center space-y-2 px-4">
                <h3 className="text-lg md:text-xl font-semibold text-foreground">尚未進行摘要</h3>
                <p className="text-sm text-muted-foreground max-w-md">
                  點擊下方按鈕開始使用 AI 為這部影片生成詳細摘要
                </p>
              </div>
              <Button
                onClick={handleGenerateSummary}
                size="lg"
                className="h-11 md:h-12 px-6 md:px-8 bg-primary text-primary-foreground hover:bg-primary/90"
              >
                <Sparkles className="w-4 h-4 md:w-5 md:h-5 mr-2" />
                開始摘要
              </Button>
            </>
          )}
        </div>
      ) : isGenerating ? (
        <div className="flex flex-col items-center justify-center py-12 md:py-20 space-y-4 md:space-y-6">
          <div className="w-20 h-20 md:w-24 md:h-24 rounded-full bg-primary/10 flex items-center justify-center">
            <RefreshCw className="w-10 h-10 md:w-12 md:h-12 text-primary animate-spin" />
          </div>
          <div className="text-center space-y-2 px-4">
            <h3 className="text-lg md:text-xl font-semibold text-foreground">正在生成摘要...</h3>
            <p className="text-sm text-muted-foreground">AI 正在分析影片內容</p>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* 左側：主要摘要內容 */}
          <Card className="border-border bg-card lg:col-span-2">
            <CardHeader className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 p-4 md:p-6">
              <div>
                <CardTitle className="text-base md:text-lg text-card-foreground">AI 摘要</CardTitle>
                <CardDescription className="text-sm">AI 生成的影片內容分析</CardDescription>
              </div>
              <Button
                onClick={handleGenerateSummary}
                disabled={isGenerating}
                className="bg-primary text-primary-foreground hover:bg-primary/90 text-sm w-full sm:w-auto"
              >
                {isGenerating ? (
                  <>
                    <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                    生成中...
                  </>
                ) : (
                  <>
                    <Sparkles className="w-4 h-4 mr-2" />
                    重新生成
                  </>
                )}
              </Button>
            </CardHeader>
            <CardContent className="p-4 md:p-6">
              <div className="prose prose-lg prose-invert max-w-none prose-headings:text-foreground prose-headings:font-bold prose-p:text-foreground prose-li:text-foreground prose-a:text-primary prose-a:underline hover:prose-a:text-primary/80">
                <div className="p-4 md:p-6 rounded-lg bg-secondary/50 border border-border text-sm md:text-base leading-relaxed">
                  <ReactMarkdown
                    components={{
                      a: ({ node, href, children, ...props }) => {
                        // 檢查是否是 YouTube 時間戳記連結
                        const isTimestamp = href && href.includes('youtube.com') && href.includes('t=')

                        if (isTimestamp) {
                          return (
                            <a
                              {...props}
                              href={href}
                              onClick={(e) => handleTimestampClick(e, href)}
                              className="text-primary hover:text-primary/80 underline cursor-pointer transition-colors font-medium"
                              title="點擊在平台內播放"
                            >
                              {children}
                            </a>
                          )
                        }

                        return (
                          <a
                            {...props}
                            href={href}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-primary hover:text-primary/80 underline cursor-pointer transition-colors"
                          >
                            {children}
                          </a>
                        )
                      },
                    }}
                  >
                    {summary}
                  </ReactMarkdown>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* 右側：筆記與下載 */}
          <div className="lg:col-span-1 space-y-6">
            {/* 筆記區塊 */}
            <Card className="border-border bg-card">
              <CardHeader className="p-4 md:p-6">
                <div className="flex items-center gap-2">
                  <FileText className="w-5 h-5 text-primary" />
                  <CardTitle className="text-base md:text-lg text-card-foreground">個人筆記</CardTitle>
                </div>
                <CardDescription className="text-sm">記錄您的想法和重點</CardDescription>
              </CardHeader>
              <CardContent className="p-4 md:p-6 pt-0 space-y-3">
                <Textarea
                  value={customNotes}
                  onChange={(e) => setCustomNotes(e.target.value)}
                  placeholder="在此記錄您對這部影片的筆記、想法或重點..."
                  className="min-h-[200px] resize-none bg-secondary/30 border-border"
                />
                <Button
                  onClick={handleSaveNotes}
                  disabled={isSavingNotes}
                  className="w-full bg-primary text-primary-foreground hover:bg-primary/90 text-sm"
                >
                  {isSavingNotes ? (
                    <>
                      <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                      儲存中...
                    </>
                  ) : (
                    <>
                      <Save className="w-4 h-4 mr-2" />
                      儲存筆記
                    </>
                  )}
                </Button>
              </CardContent>
            </Card>

            {/* 下載區塊 */}
            <Card className="border-border bg-card">
              <CardHeader className="p-4 md:p-6">
                <div className="flex items-center gap-2">
                  <Download className="w-5 h-5 text-primary" />
                  <CardTitle className="text-base md:text-lg text-card-foreground">匯出摘要</CardTitle>
                </div>
                <CardDescription className="text-sm">下載 AI 摘要與筆記</CardDescription>
              </CardHeader>
              <CardContent className="p-4 md:p-6 pt-0 space-y-3">
                <Button
                  onClick={() => {
                    // 下載 Markdown 格式
                    const content = `# AI 影片摘要\n\n${summary}\n\n---\n\n## 個人筆記\n\n${customNotes || '(無筆記)'}`
                    const blob = new Blob([content], { type: 'text/markdown' })
                    const url = URL.createObjectURL(blob)
                    const a = document.createElement('a')
                    a.href = url
                    a.download = `video-summary-${videoId}.md`
                    a.click()
                    URL.revokeObjectURL(url)

                    toast({
                      title: "下載成功",
                      description: "摘要已下載為 Markdown 格式",
                    })
                  }}
                  variant="outline"
                  className="w-full"
                >
                  <Download className="w-4 h-4 mr-2" />
                  下載 Markdown
                </Button>
                <Button
                  onClick={() => {
                    // 下載純文字格式
                    const content = `AI 影片摘要\n${'='.repeat(50)}\n\n${summary.replace(/[#*`]/g, '')}\n\n${'='.repeat(50)}\n\n個人筆記\n${'='.repeat(50)}\n\n${customNotes || '(無筆記)'}`
                    const blob = new Blob([content], { type: 'text/plain' })
                    const url = URL.createObjectURL(blob)
                    const a = document.createElement('a')
                    a.href = url
                    a.download = `video-summary-${videoId}.txt`
                    a.click()
                    URL.revokeObjectURL(url)

                    toast({
                      title: "下載成功",
                      description: "摘要已下載為純文字格式",
                    })
                  }}
                  variant="outline"
                  className="w-full"
                >
                  <Download className="w-4 h-4 mr-2" />
                  下載純文字
                </Button>
              </CardContent>
            </Card>
          </div>
        </div>
      )}
    </div>
  )
}
