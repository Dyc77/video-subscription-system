'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { LogOut, Loader2 } from 'lucide-react';
import { getUserInfoFromToken, logout } from '@/lib/api';
import Swal from 'sweetalert2';

export function UserAvatarMenu() {
  const router = useRouter();
  const [userInfo, setUserInfo] = useState<{ email: string; picture?: string } | null>(null);
  const [isLoggingOut, setIsLoggingOut] = useState(false);

  useEffect(() => {
    const info = getUserInfoFromToken();
    setUserInfo(info);
  }, []);

  const handleLogout = () => {
    setIsLoggingOut(true);

    logout();

    Swal.fire({
      icon: 'success',
      title: '系統準備登出',
      text: '3 秒後將跳轉至登入頁面...',
      timer: 3000,
      showConfirmButton: false
    });

    setTimeout(() => {
      router.push('/');
    }, 3000);
  };

  if (!userInfo) return null;

  // 從 email 提取首字母作為頭像 fallback
  const initials = userInfo.email
    .split('@')[0]
    .substring(0, 2)
    .toUpperCase();

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger asChild disabled={isLoggingOut}>
          <button className="relative rounded-full focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2" disabled={isLoggingOut}>
            <Avatar className="h-9 w-9 cursor-pointer border-2 border-border hover:border-primary transition-colors">
              <AvatarImage src={userInfo.picture} alt={userInfo.email} />
              <AvatarFallback className="bg-primary/10 text-primary font-semibold">
                {isLoggingOut ? <Loader2 className="h-4 w-4 animate-spin" /> : initials}
              </AvatarFallback>
            </Avatar>
          </button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-56">
          <DropdownMenuLabel className="font-normal">
            <div className="flex flex-col space-y-1">
              <p className="text-sm font-medium leading-none">我的帳號</p>
              <p className="text-xs leading-none text-muted-foreground truncate">
                {userInfo.email}
              </p>
            </div>
          </DropdownMenuLabel>
          <DropdownMenuSeparator />
          <DropdownMenuItem
            onClick={handleLogout}
            disabled={isLoggingOut}
            className="text-destructive focus:text-destructive focus:bg-destructive/10 cursor-pointer"
          >
            {isLoggingOut ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                <span>登出中...</span>
              </>
            ) : (
              <>
                <LogOut className="mr-2 h-4 w-4" />
                <span>登出</span>
              </>
            )}
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      {/* 登出中的全屏遮罩 */}
      {isLoggingOut && (
        <div className="fixed inset-0 z-[9999] bg-background/80 backdrop-blur-sm flex items-center justify-center">
          <div className="bg-card border border-border rounded-lg p-6 shadow-lg flex flex-col items-center gap-4">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
            <div className="text-center">
              <p className="font-semibold text-foreground">系統準備登出</p>
              <p className="text-sm text-muted-foreground mt-1">3 秒後將跳轉至登入頁面...</p>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
