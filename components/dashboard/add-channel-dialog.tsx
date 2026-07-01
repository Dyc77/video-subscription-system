'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Plus, Loader2 } from 'lucide-react';
import Swal from 'sweetalert2';
import { addChannel, type Channel } from '@/lib/api';

interface AddChannelDialogProps {
  onChannelAdded?: (channel: Channel) => void;
}

export function AddChannelDialog({ onChannelAdded }: AddChannelDialogProps) {
  const [open, setOpen] = useState(false);
  const [channelUrl, setChannelUrl] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!channelUrl.trim()) {
      Swal.fire({
        icon: 'error',
        title: '錯誤',
        text: '請輸入頻道網址',
        confirmButtonText: '確定'
      });
      return;
    }

    // 清理網址：移除空白和查詢參數（如手機版的 ?si=xxx）
    let cleanUrl = channelUrl.trim();

    // 驗證是否為 YouTube 網址
    if (!cleanUrl.includes('youtube.com/')) {
      Swal.fire({
        icon: 'error',
        title: '錯誤',
        text: '請輸入有效的 YouTube 頻道網址',
        confirmButtonText: '確定'
      });
      return;
    }

    setLoading(true);

    try {
      const channel = await addChannel(cleanUrl);

      await Swal.fire({
        icon: 'success',
        title: '頻道新增成功！',
        text: `已成功訂閱 ${channel.title}`,
        confirmButtonText: '確定'
      });

      // 重置表單
      setChannelUrl('');
      setOpen(false);

      // 通知父組件
      onChannelAdded?.(channel);
    } catch (error) {
      console.error('新增頻道失敗:', error);
      const errorMessage = (error as Error).message;

      // 檢查是否為已訂閱的錯誤
      if (errorMessage.includes('已經訂閱')) {
        Swal.fire({
          icon: 'warning',
          title: '頻道已存在',
          text: errorMessage,
          confirmButtonText: '確定'
        });
      } else {
        Swal.fire({
          icon: 'error',
          title: '新增頻道失敗',
          text: errorMessage,
          confirmButtonText: '確定'
        });
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button className="gap-2">
          <Plus className="w-4 h-4" />
          新增頻道
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[525px]">
        <DialogHeader>
          <DialogTitle>新增 YouTube 頻道</DialogTitle>
          <DialogDescription>
            輸入 YouTube 頻道網址（支援手機版網址），系統會自動解析並訂閱該頻道
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4 mt-4">
          <div className="space-y-2">
            <Label htmlFor="channel-url">頻道網址</Label>
            <Input
              id="channel-url"
              placeholder="https://www.youtube.com/@channelname"
              value={channelUrl}
              onChange={(e) => setChannelUrl(e.target.value)}
              disabled={loading}
            />
            <p className="text-sm text-muted-foreground">
              支援格式：
            </p>
            <ul className="text-xs text-muted-foreground space-y-1 ml-4">
              <li>• https://www.youtube.com/@channelhandle</li>
              <li>• https://www.youtube.com/channel/UCxxxxxx</li>
              <li>• https://www.youtube.com/c/CustomName</li>
              <li>• https://www.youtube.com/user/username</li>
            </ul>
          </div>
          <div className="flex justify-end gap-3">
            <Button
              type="button"
              variant="outline"
              onClick={() => setOpen(false)}
              disabled={loading}
            >
              取消
            </Button>
            <Button type="submit" disabled={loading}>
              {loading && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
              {loading ? '新增中...' : '新增頻道'}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
