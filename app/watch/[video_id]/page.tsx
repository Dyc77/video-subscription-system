'use client';

import { useParams } from 'next/navigation';
import { useState, useEffect } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Loader2, ExternalLink } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface VideoInfo {
  video_id: string;
  title: string | null;
  channel_title: string | null;
  thumbnail_url: string | null;
}

export default function PublicWatchPage() {
  const params = useParams();
  const video_id = params.video_id as string;
  const [videoInfo, setVideoInfo] = useState<VideoInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [startTime, setStartTime] = useState<number>(0);

  useEffect(() => {
    if (!video_id) return;

    // 從 URL 查詢參數取得時間戳記
    const urlParams = new URLSearchParams(window.location.search);
    const timeParam = urlParams.get('t');
    if (timeParam) {
      const seconds = parseInt(timeParam);
      if (!isNaN(seconds)) {
        setStartTime(seconds);
      }
    }

    // 從 API 載入影片基本資訊(不需登入)
    const loadVideoInfo = async () => {
      try {
        const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/public/video/${video_id}`);
        if (response.ok) {
          const data = await response.json();
          setVideoInfo(data);
        }
      } catch (error) {
        console.error('載入影片資訊失敗:', error);
      } finally {
        setLoading(false);
      }
    };

    loadVideoInfo();
  }, [video_id]);

  const openYouTube = () => {
    window.open(`https://www.youtube.com/watch?v=${video_id}`, '_blank');
  };

  if (!video_id) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-destructive mb-2">無效的影片 ID</h1>
          <p className="text-muted-foreground">請確認連結是否正確</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-background to-secondary/20">
      {/* Header */}
      <header className="bg-background/80 backdrop-blur-sm border-b border-border sticky top-0 z-10">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-primary rounded-lg flex items-center justify-center">
              <span className="text-primary-foreground font-bold text-lg">VH</span>
            </div>
            <div>
              <h1 className="text-xl font-bold text-foreground">VideoHub</h1>
              <p className="text-xs text-muted-foreground">影片播放</p>
            </div>
          </div>
          <Badge variant="outline" className="hidden sm:inline-flex">
            公開播放
          </Badge>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-6 md:py-12 max-w-6xl">
        <Card className="border-border bg-card shadow-xl overflow-hidden">
          {loading ? (
            <CardContent className="p-12 flex flex-col items-center justify-center">
              <Loader2 className="w-12 h-12 animate-spin text-primary mb-4" />
              <p className="text-muted-foreground">載入中...</p>
            </CardContent>
          ) : (
            <>
              {/* Video Player */}
              <div className="aspect-video w-full bg-black relative">
                <iframe
                  width="100%"
                  height="100%"
                  src={`https://www.youtube.com/embed/${video_id}?start=${startTime}&autoplay=${startTime > 0 ? 1 : 0}&rel=0&modestbranding=1`}
                  title="YouTube video player"
                  frameBorder="0"
                  allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
                  allowFullScreen
                  className="w-full h-full"
                ></iframe>
              </div>

              {/* Video Info */}
              <CardContent className="p-6 space-y-4">
                {videoInfo?.title && (
                  <div>
                    <h2 className="text-2xl font-bold text-foreground mb-2">
                      {videoInfo.title}
                    </h2>
                    {videoInfo.channel_title && (
                      <p className="text-muted-foreground">
                        頻道：{videoInfo.channel_title}
                      </p>
                    )}
                  </div>
                )}

                {/* Action Buttons */}
                <div className="flex flex-wrap gap-3 pt-4 border-t border-border">
                  <Button
                    onClick={openYouTube}
                    variant="default"
                    className="flex-1 sm:flex-none"
                  >
                    <ExternalLink className="w-4 h-4 mr-2" />
                    在 YouTube 觀看
                  </Button>

                  <Button
                    onClick={() => window.location.href = '/'}
                    variant="outline"
                    className="flex-1 sm:flex-none"
                  >
                    返回首頁
                  </Button>
                </div>

                {/* Info Note */}
                <div className="bg-secondary/50 rounded-lg p-4 mt-6">
                  <p className="text-sm text-muted-foreground text-center">
                    💡 這是公開播放頁面,不需要登入即可觀看
                  </p>
                  <p className="text-xs text-muted-foreground text-center mt-2">
                    想要更多功能？<a href="/" className="text-primary hover:underline ml-1">立即註冊 VideoHub</a>
                  </p>
                </div>
              </CardContent>
            </>
          )}
        </Card>
      </main>

      {/* Footer */}
      <footer className="mt-12 py-6 border-t border-border bg-background/50">
        <div className="container mx-auto px-4 text-center">
          <p className="text-sm text-muted-foreground">
            © 2024 VideoHub. 影片來源於 YouTube
          </p>
        </div>
      </footer>
    </div>
  );
}
