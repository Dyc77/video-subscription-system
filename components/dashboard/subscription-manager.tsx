'use client';

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { Trash2, RefreshCw, Video, ExternalLink, Loader2, Download, Bell, BellOff } from 'lucide-react';
import Swal from 'sweetalert2';
import { getMySubscriptions, unsubscribeChannel, scanChannel, scanAllSubscriptions, toggleChannelNotification, type Channel } from '@/lib/api';
import { AddChannelDialog } from './add-channel-dialog';

export function SubscriptionManager() {
  const [subscriptions, setSubscriptions] = useState<Channel[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [scanningAll, setScanningAll] = useState(false);
  const [scanningChannels, setScanningChannels] = useState<Set<string>>(new Set());

  // 載入訂閱列表
  const loadSubscriptions = async () => {
    try {
      const data = await getMySubscriptions();
      setSubscriptions(data);
    } catch (error) {
      console.error('載入訂閱失敗:', error);
      Swal.fire({
        icon: 'error',
        title: '載入訂閱失敗',
        text: (error as Error).message,
        confirmButtonText: '確定'
      });
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadSubscriptions();
  }, []);

  const handleRefreshAll = () => {
    setRefreshing(true);
    loadSubscriptions();
  };

  const handleRemoveSubscription = async (channel: Channel) => {
    // 顯示確認對話框
    const result = await Swal.fire({
      icon: 'warning',
      title: '確定要取消訂閱？',
      html: `
        <div style="text-align: left; padding: 10px;">
          <p style="margin-bottom: 10px;">您即將取消訂閱以下頻道：</p>
          <div style="background: #f3f4f6; padding: 12px; border-radius: 6px; margin-bottom: 10px;">
            <p style="font-weight: bold; color: #1f2937;">${channel.title}</p>
          </div>
          <p style="color: #6b7280; font-size: 14px;">⚠️ 取消訂閱後，您將不再收到此頻道的新影片通知</p>
        </div>
      `,
      showCancelButton: true,
      confirmButtonText: '確定取消訂閱',
      cancelButtonText: '保留訂閱',
      confirmButtonColor: '#dc2626',
      cancelButtonColor: '#6b7280',
    });

    if (!result.isConfirmed) {
      return;
    }

    try {
      await unsubscribeChannel(channel.channel_id);

      Swal.fire({
        icon: 'success',
        title: '取消訂閱成功',
        text: `已取消訂閱 ${channel.title}`,
        confirmButtonText: '確定',
        timer: 2000
      });

      // 從列表中移除
      setSubscriptions(subscriptions.filter((sub) => sub.channel_id !== channel.channel_id));
    } catch (error) {
      console.error('取消訂閱失敗:', error);
      Swal.fire({
        icon: 'error',
        title: '取消訂閱失敗',
        text: (error as Error).message,
        confirmButtonText: '確定'
      });
    }
  };

  const handleChannelAdded = () => {
    // 重新載入訂閱列表
    loadSubscriptions();
  };

  const handleScanChannel = async (channel: Channel) => {
    setScanningChannels(prev => new Set(prev).add(channel.channel_id));

    try {
      const result = await scanChannel(channel.channel_id);

      Swal.fire({
        icon: 'success',
        title: '掃描已啟動',
        text: `${result.channel_title} 正在背景掃描中，完成後請重新整理影片列表`,
        confirmButtonText: '確定',
        timer: 2500
      });
    } catch (error) {
      console.error('掃描頻道失敗:', error);
      Swal.fire({
        icon: 'error',
        title: '掃描頻道失敗',
        text: (error as Error).message,
        confirmButtonText: '確定'
      });
    } finally {
      setScanningChannels(prev => {
        const newSet = new Set(prev);
        newSet.delete(channel.channel_id);
        return newSet;
      });
    }
  };

  const handleScanAll = async () => {
    setScanningAll(true);

    try {
      const result = await scanAllSubscriptions();

      Swal.fire({
        icon: 'success',
        title: '掃描已啟動',
        text: `${result.total_channels} 個頻道正在背景掃描中，完成後請重新整理影片列表`,
        confirmButtonText: '確定',
        timer: 3000
      });
    } catch (error) {
      console.error('批量掃描失敗:', error);
      Swal.fire({
        icon: 'error',
        title: '批量掃描失敗',
        text: (error as Error).message,
        confirmButtonText: '確定'
      });
    } finally {
      setScanningAll(false);
    }
  };

  const handleToggleNotification = async (channel: Channel, enabled: boolean) => {
    try {
      await toggleChannelNotification(channel.channel_id, enabled);

      // 更新本地状态
      setSubscriptions(subscriptions.map(sub =>
        sub.channel_id === channel.channel_id
          ? { ...sub, is_notification_enabled: enabled ? 1 : 0 }
          : sub
      ));

      Swal.fire({
        icon: 'success',
        title: enabled ? '已開啟通知' : '已關閉通知',
        text: `${channel.title} 的通知已${enabled ? '開啟' : '關閉'}`,
        confirmButtonText: '確定',
        timer: 2000
      });
    } catch (error) {
      console.error('更新通知設定失敗:', error);
      Swal.fire({
        icon: 'error',
        title: '更新通知設定失敗',
        text: (error as Error).message,
        confirmButtonText: '確定'
      });
    }
  };

  if (loading) {
    return (
      <div className="p-4 md:p-6 flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <Loader2 className="w-8 h-8 animate-spin mx-auto mb-4 text-primary" />
          <p className="text-muted-foreground">載入訂閱中...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="w-[90%] md:w-[80%] lg:w-[75%] mx-auto p-4 md:p-6 space-y-4 md:space-y-6">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl md:text-2xl font-bold text-foreground">訂閱管理</h2>
          <p className="text-sm text-muted-foreground">管理您的 YouTube 頻道訂閱</p>
        </div>
        <div className="flex flex-wrap gap-2 md:gap-3 w-full sm:w-auto">
          <Button
            onClick={handleScanAll}
            variant="outline"
            disabled={scanningAll || subscriptions.length === 0}
            className="flex-1 sm:flex-none text-sm"
          >
            <Download className={`w-4 h-4 mr-2 ${scanningAll ? 'animate-bounce' : ''}`} />
            <span className="hidden sm:inline">{scanningAll ? '掃描中...' : '抓取所有影片'}</span>
            <span className="sm:hidden">抓取影片</span>
          </Button>
          <Button
            onClick={handleRefreshAll}
            variant="outline"
            disabled={refreshing}
            className="flex-1 sm:flex-none text-sm"
          >
            <RefreshCw className={`w-4 h-4 mr-2 ${refreshing ? 'animate-spin' : ''}`} />
            <span className="hidden sm:inline">重新整理</span>
            <span className="sm:hidden">重整</span>
          </Button>
          <AddChannelDialog onChannelAdded={handleChannelAdded} />
        </div>
      </div>

      <div className="space-y-4">
        <h3 className="text-lg font-semibold text-foreground">
          您的訂閱 ({subscriptions.length})
        </h3>

        {subscriptions.length === 0 ? (
          <Card className="border-dashed">
            <CardContent className="p-8 md:p-12 text-center">
              <Video className="w-10 h-10 md:w-12 md:h-12 mx-auto mb-4 text-muted-foreground" />
              <h3 className="text-base md:text-lg font-semibold mb-2">還沒有訂閱任何頻道</h3>
              <p className="text-sm text-muted-foreground mb-6">
                點擊上方「新增頻道」按鈕開始訂閱您喜歡的 YouTube 頻道
              </p>
              <AddChannelDialog onChannelAdded={handleChannelAdded} />
            </CardContent>
          </Card>
        ) : (
          <div className="grid gap-3 md:gap-4 lg:grid-cols-2">
            {subscriptions.map((sub) => (
              <Card
                key={sub.channel_no}
                className="border-border bg-card hover:border-primary/30 transition-colors"
              >
                <CardContent className="p-3 md:p-4">
                  <div className="flex items-center gap-3 md:gap-4">
                    {/* 通知开关 - 放在最左边 */}
                    <div className="flex items-center shrink-0">
                      <Switch
                        checked={sub.is_notification_enabled === 1}
                        onCheckedChange={(checked) => handleToggleNotification(sub, checked)}
                        title={sub.is_notification_enabled === 1 ? '點擊關閉通知' : '點擊開啟通知'}
                      />
                    </div>

                    <img
                      src={sub.thumbnail_url || '/placeholder.svg'}
                      alt={sub.title || 'Channel'}
                      className="w-12 h-12 sm:w-14 sm:h-14 md:w-16 md:h-16 rounded-full border-2 border-border object-cover shrink-0"
                      onError={(e) => {
                        const target = e.target as HTMLImageElement;
                        target.src = '/placeholder.svg';
                      }}
                    />
                    <div className="flex-1 min-w-0">
                      <div className="flex flex-col sm:flex-row sm:items-center gap-1 sm:gap-2 mb-1">
                        <h4 className="font-semibold text-card-foreground truncate text-base md:text-lg">
                          {sub.title || 'Unknown Channel'}
                        </h4>
                        <Badge
                          variant={sub.channel_status === 1 ? 'default' : 'secondary'}
                          className="shrink-0 w-fit text-xs"
                        >
                          <Video className="w-3 h-3 mr-1" />
                          {sub.channel_status === 1 ? '監控中' : '已停用'}
                        </Badge>
                      </div>
                      <div className="flex flex-col sm:flex-row sm:items-center gap-2 mt-1">
                        <p className="text-xs text-muted-foreground">
                          訂閱時間: {new Date(sub.create_time).toLocaleDateString('zh-TW')}
                        </p>
                        <div className="flex items-center gap-1.5">
                          {sub.is_notification_enabled === 1 ? (
                            <Bell className="w-3 h-3 text-primary" />
                          ) : (
                            <BellOff className="w-3 h-3 text-muted-foreground" />
                          )}
                          <span className="text-xs text-muted-foreground">
                            {sub.is_notification_enabled === 1 ? '通知已開啟' : '通知已關閉'}
                          </span>
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-1 md:gap-2">
                      {/* <Button
                        variant="ghost"
                        size="icon"
                        className="text-muted-foreground hover:text-foreground h-8 w-8 md:h-10 md:w-10"
                        onClick={() => handleScanChannel(sub)}
                        disabled={scanningChannels.has(sub.channel_id)}
                        title="抓取影片"
                      >
                        <Download className={`w-4 h-4 ${scanningChannels.has(sub.channel_id) ? 'animate-bounce' : ''}`} />
                      </Button> */}
                      <Button
                        variant="ghost"
                        size="icon"
                        className="text-muted-foreground hover:text-foreground h-8 w-8 md:h-10 md:w-10 hidden sm:flex"
                        onClick={() => {
                          window.open(
                            `https://www.youtube.com/channel/${sub.channel_id}`,
                            '_blank'
                          );
                        }}
                        title="在 YouTube 開啟"
                      >
                        <ExternalLink className="w-4 h-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => handleRemoveSubscription(sub)}
                        className="text-destructive hover:text-destructive hover:bg-destructive/10 h-8 w-8 md:h-10 md:w-10"
                        title="取消訂閱"
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
