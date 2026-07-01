'use client';

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Dialog, DialogContent, DialogTitle } from '@/components/ui/dialog';
import { VisuallyHidden } from '@radix-ui/react-visually-hidden';
import { Play, Loader2, Calendar, Eye, List, Bookmark, Sparkles, X, FileText, ExternalLink } from 'lucide-react';
import Swal from 'sweetalert2';
import { getUserVideos, getMySubscriptions, toggleFavorite, type Video, type Channel } from '@/lib/api';

interface VideoListProps {
  onVideoSelect: (videoId: string) => void;
}

export function VideoList({ onVideoSelect }: VideoListProps) {
  const [videos, setVideos] = useState<Video[]>([]);
  const [channels, setChannels] = useState<Channel[]>([]);
  const [selectedChannelId, setSelectedChannelId] = useState<string>('all');
  const [activeTab, setActiveTab] = useState<string>('all');
  const [loading, setLoading] = useState(true);
  
  const [playingVideoId, setPlayingVideoId] = useState<string | null>(null);

  // ... (省略中間未修改的載入邏輯: loadChannels, loadVideos, useEffect, handleChannelChange) ...
  // 請保留原本的 loadChannels, loadVideos, useEffect 等函式
  
  // 為了完整性，這裡重複顯示相關載入函式，實際使用時請確保沒刪除您的原有邏輯
  const loadChannels = async () => {
    try {
      const data = await getMySubscriptions();
      setChannels(data);
    } catch (error) {
      console.error('載入頻道失敗:', error);
      Swal.fire({
        icon: 'error',
        title: '載入頻道失敗',
        text: (error as Error).message,
        confirmButtonText: '確定'
      });
    }
  };

  const loadVideos = async (channelId?: string) => {
    setLoading(true);
    try {
      const data = await getUserVideos(channelId === 'all' ? undefined : channelId);
      setVideos(data);
    } catch (error) {
      console.error('載入影片失敗:', error);
      Swal.fire({
        icon: 'error',
        title: '載入影片失敗',
        text: (error as Error).message,
        confirmButtonText: '確定'
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadChannels();
    loadVideos();
  }, []);

  const handleChannelChange = (channelId: string) => {
    setSelectedChannelId(channelId);
    loadVideos(channelId);
    handleClosePlayer();
  };

  const handlePlayVideo = (videoId: string) => {
    setPlayingVideoId(videoId);
  };

  const handleClosePlayer = () => {
    setPlayingVideoId(null);
  };

  const handleToggleFavorite = async (videoId: string, event: React.MouseEvent) => {
    event.stopPropagation();
    try {
      const result = await toggleFavorite(videoId);
      setVideos(videos.map(v => v.video_id === videoId ? { ...v, is_favorite: result.is_favorite } : v));
      Swal.fire({
        icon: 'success',
        title: result.message || '操作成功',
        confirmButtonText: '確定',
        timer: 1500,
        showConfirmButton: false
      });
    } catch (error) {
      console.error('收藏操作失敗:', error);
      Swal.fire({
        icon: 'error',
        title: '操作失敗',
        text: (error as Error).message,
        confirmButtonText: '確定'
      });
    }
  };

  const getFilteredVideos = () => {
    if (activeTab === 'favorites') {
      return videos.filter(v => v.is_favorite === 1);
    }
    return videos;
  };

  const formatDate = (dateString: string | null) => {
    if (!dateString) return '未知日期';
    const date = new Date(dateString);
    return date.toLocaleDateString('zh-TW', { year: 'numeric', month: '2-digit', day: '2-digit' });
  };

  // 輔助函式：開啟 YouTube 原站
  const openOriginalYoutube = (videoId: string) => {
    window.open(`https://www.youtube.com/watch?v=${videoId}`, '_blank');
  };

  if (loading) {
    return (
      <div className="p-4 md:p-6 flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <Loader2 className="w-8 h-8 animate-spin mx-auto mb-4 text-primary" />
          <p className="text-muted-foreground">載入影片中...</p>
        </div>
      </div>
    );
  }

  const filteredVideos = getFilteredVideos();

  return (
    <div className="w-[90%] md:w-[80%] lg:w-[75%] mx-auto p-4 md:p-6 space-y-4 md:space-y-6">
      {/* 標題和頻道選單 */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl md:text-2xl font-bold text-foreground">影片庫</h2>
          <p className="text-sm text-muted-foreground">瀏覽您訂閱頻道的影片</p>
        </div>
        <div className="flex items-center gap-3 w-full sm:w-auto">
          <Select value={selectedChannelId} onValueChange={handleChannelChange}>
            <SelectTrigger className="w-full sm:w-[240px] h-11 border-2 border-primary/20 hover:border-primary/40 focus:border-primary shadow-sm">
              <SelectValue placeholder="選擇頻道" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all" className="font-medium">📺 全部頻道</SelectItem>
              {channels.map((channel) => (
                <SelectItem key={channel.channel_no} value={channel.channel_id}>
                  {channel.title || 'Unknown Channel'}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="bg-secondary border border-border">
          <TabsTrigger value="all" className="data-[state=active]:bg-primary data-[state=active]:text-primary-foreground">
            <List className="w-4 h-4 mr-2" /> 總覽
          </TabsTrigger>
          <TabsTrigger value="favorites" className="data-[state=active]:bg-primary data-[state=active]:text-primary-foreground">
            <Bookmark className="w-4 h-4 mr-2" /> 收藏
          </TabsTrigger>
        </TabsList>
      </Tabs>

      {/* 影片播放 Modal */}
      <Dialog open={!!playingVideoId} onOpenChange={(open) => !open && handleClosePlayer()}>
        <DialogContent className="!w-[70vw] !max-w-[70vw] sm:!max-w-[70vw] p-0">
          <VisuallyHidden>
            <DialogTitle>影片播放</DialogTitle>
          </VisuallyHidden>
          <div className="aspect-video w-full bg-black">
            {playingVideoId && (
              <iframe
                width="100%"
                height="100%"
                src={`https://www.youtube.com/embed/${playingVideoId}?autoplay=1&rel=0&modestbranding=1`}
                title="YouTube video player"
                frameBorder="0"
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
                allowFullScreen
                className="w-full h-full"
              ></iframe>
            )}
          </div>
          <div className="p-4 flex flex-wrap gap-2 justify-end bg-secondary/30">
            <Button
              onClick={() => playingVideoId && openOriginalYoutube(playingVideoId)}
              variant="outline"
              size="sm"
            >
              <ExternalLink className="mr-2 h-4 w-4" />
              在 YouTube 觀看
            </Button>
            <Button
              onClick={() => {
                if (playingVideoId) {
                  handleClosePlayer();
                  onVideoSelect(playingVideoId);
                }
              }}
              variant="default"
              size="sm"
            >
              <FileText className="mr-2 h-4 w-4" />
              查看 AI 摘要
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* 影片列表 */}
      {filteredVideos.length === 0 ? (
        <Card className="border-dashed">
          <CardContent className="p-8 md:p-12 text-center">
            <Eye className="w-10 h-10 md:w-12 md:h-12 mx-auto mb-4 text-muted-foreground" />
            <h3 className="text-base md:text-lg font-semibold mb-2">
              {activeTab === 'favorites' ? '還沒有收藏的影片' : '還沒有影片'}
            </h3>
            <p className="text-sm text-muted-foreground">
              {activeTab === 'favorites'
                ? '點擊影片上的書籤圖示來收藏影片'
                : selectedChannelId === 'all'
                ? '您的訂閱頻道中還沒有影片，請先訂閱頻道並抓取影片'
                : '此頻道還沒有影片，請點擊「抓取影片」按鈕'}
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 md:gap-6">
          {filteredVideos.map((video) => (
            <VideoCard
              key={video.video_no}
              video={video}
              isPlaying={playingVideoId === video.video_id}
              onPlay={() => handlePlayVideo(video.video_id)}
              onSummary={() => onVideoSelect(video.video_id)}
              onToggleFavorite={(e) => handleToggleFavorite(video.video_id, e)}
              formatDate={formatDate}
            />
          ))}
        </div>
      )}
    </div>
  );
}

// ... (VideoCard 元件保持不變) ...
interface VideoCardProps {
  video: Video;
  isPlaying: boolean;
  onPlay: () => void;
  onSummary: () => void;
  onToggleFavorite: (e: React.MouseEvent) => void;
  formatDate: (date: string | null) => string;
}

function VideoCard({ video, isPlaying, onPlay, onSummary, onToggleFavorite, formatDate }: VideoCardProps) {
  const isFavorite = video.is_favorite === 1;

  return (
    <Card
      className={`overflow-hidden border-border bg-card hover:border-primary/30 transition-all group ${
        isPlaying ? 'ring-2 ring-primary shadow-lg' : ''
      }`}
    >
      <div className="relative aspect-video bg-muted">
        <img
          src={video.thumbnail_url || '/placeholder.svg'}
          alt={video.title || 'Video'}
          className="w-full h-full object-cover"
          onError={(e) => {
            const target = e.target as HTMLImageElement;
            target.src = '/placeholder.svg';
          }}
        />
        <div className="absolute inset-0 bg-background/60 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
          <Button
            size="icon"
            variant="secondary"
            className="w-14 h-14 rounded-full bg-primary text-primary-foreground hover:bg-primary/90"
            onClick={onPlay}
          >
            <Play className="w-6 h-6" />
          </Button>
        </div>
      </div>
      <CardContent className="p-4 space-y-3">
        <div>
          <h3 className="font-semibold text-card-foreground line-clamp-2 leading-tight min-h-[2.5rem]" title={video.title || undefined}>
            {video.title || 'Untitled Video'}
          </h3>
          <div className="flex items-center gap-2 mt-2 text-xs text-muted-foreground">
            <Calendar className="w-3 h-3" />
            <span>{formatDate(video.published_at)}</span>
          </div>
        </div>
        <div className="flex items-center gap-2 pt-2">
          <Button
            variant="outline"
            onClick={onPlay}
            className="flex-1 h-9 text-xs sm:text-sm hover:bg-primary hover:text-primary-foreground"
            title="播放"
          >
            <Play className="w-3.5 h-3.5 sm:w-4 sm:h-4 sm:mr-1.5" />
            <span className="hidden sm:inline">播放</span>
          </Button>
          <Button
            variant="outline"
            onClick={onSummary}
            className="flex-1 h-9 text-xs sm:text-sm hover:bg-accent hover:text-accent-foreground"
            title="查看摘要"
          >
            <Sparkles className="w-3.5 h-3.5 sm:w-4 sm:h-4 sm:mr-1.5" />
            <span className="hidden sm:inline">摘要</span>
          </Button>
          <Button
            variant="outline"
            onClick={onToggleFavorite}
            className={`flex-1 h-9 text-xs sm:text-sm ${
              isFavorite
                ? 'bg-amber-500/10 text-amber-600 hover:bg-amber-500/20 border-amber-500/30'
                : 'hover:bg-accent hover:text-accent-foreground'
            }`}
            title={isFavorite ? '取消收藏' : '加入收藏'}
          >
            <Bookmark className={`w-3.5 h-3.5 sm:w-4 sm:h-4 sm:mr-1.5 ${isFavorite ? 'fill-current' : ''}`} />
            <span className="hidden sm:inline">收藏</span>
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}