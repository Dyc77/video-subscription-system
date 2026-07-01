// API 服務層 - 統一管理所有後端 API 調用

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// 獲取 JWT Token
function getAuthToken(): string | null {
  if (typeof window !== 'undefined') {
    return localStorage.getItem('access_token');
  }
  return null;
}

// 通用請求函數
async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getAuthToken();

  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...options.headers,
  };

  if (token) {
    (headers as any)['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    // JWT 過期或無效，觸發登出
    if (response.status === 401) {
      if (typeof window !== 'undefined') {
        localStorage.removeItem('access_token');
        // 觸發自定義事件，通知應用 token 過期
        window.dispatchEvent(new CustomEvent('token-expired'));
      }
    }

    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(error.detail || `HTTP error! status: ${response.status}`);
  }

  return response.json();
}

// ============ 頻道相關 API ============

export interface Channel {
  channel_no: number;
  channel_id: string;
  title: string | null;
  thumbnail_url: string | null;
  channel_status: number;
  create_time: string;
  is_notification_enabled?: number; // 0:關閉, 1:開啟
}

export interface Subscription {
  subscription_no: number;
  user_no: number;
  channel_no: number;
  is_notification_enabled: number;
  create_time: string;
}

// 新增頻道（使用網址）
export async function addChannel(channelUrl: string): Promise<Channel> {
  return apiRequest<Channel>('/api/channel/add', {
    method: 'POST',
    body: JSON.stringify({ channel_url: channelUrl }),
  });
}

// 獲取我的訂閱列表
export async function getMySubscriptions(): Promise<Channel[]> {
  return apiRequest<Channel[]>('/api/channel/subscriptions/list');
}

// 獲取所有頻道列表
export async function getAllChannels(status?: number): Promise<Channel[]> {
  const params = status !== undefined ? `?status=${status}` : '';
  return apiRequest<Channel[]>(`/api/channel/list${params}`);
}

// 訂閱頻道
export async function subscribeChannel(channelId: string): Promise<Subscription> {
  return apiRequest<Subscription>('/api/channel/subscribe', {
    method: 'POST',
    body: JSON.stringify({ channel_id: channelId }),
  });
}

// 取消訂閱頻道
export async function unsubscribeChannel(channelId: string): Promise<{ message: string; channel_id: string }> {
  return apiRequest(`/api/channel/unsubscribe/${channelId}`, {
    method: 'DELETE',
  });
}

// 手動掃描單個頻道（RSS 抓取影片）— 背景進程，立即返回
export async function scanChannel(channelId: string): Promise<{
  message: string;
  channel_id: string;
  channel_title: string | null;
  process_id: number;
  process_name: string;
  note: string;
  status: string;
}> {
  return apiRequest(`/api/channel/scan/${channelId}`, {
    method: 'POST',
  });
}

// 手動掃描所有訂閱頻道（RSS 抓取影片）— 背景進程，立即返回
export async function scanAllSubscriptions(): Promise<{
  message: string;
  total_channels: number;
  process_id?: number;
  process_name?: string;
  note?: string;
  status: string;
}> {
  return apiRequest('/api/channel/scan/all', {
    method: 'POST',
  });
}

// 切換頻道通知開關
export async function toggleChannelNotification(channelId: string, enabled: boolean): Promise<{
  message: string;
  channel_id: string;
  is_notification_enabled: number;
}> {
  return apiRequest(`/api/channel/notification/${channelId}`, {
    method: 'PUT',
    body: JSON.stringify({ enabled }),
  });
}

// ============ 影片相關 API ============

export interface Video {
  video_no: number;
  video_id: string;
  title: string | null;
  thumbnail_url: string | null;
  video_url: string | null;
  published_at: string | null;
  channel_no: number;
  summary_status: number;
  summary_content: string | null;
  create_time: string;
  is_favorite?: number; // 可選欄位，用於收藏功能
}

export interface VideoLibrary {
  user_no: number;
  account: string;
  membership_level: number;
  video_no: number;
  video_id: string;
  video_title: string | null;
  thumbnail_url: string | null;
  published_at: string | null;
  video_url: string | null;
  channel_no: number;
  channel_title: string | null;
  channel_thumbnail: string | null;
  summary_content: string | null;
  summary_status: number;
  is_favorite: number;
  is_watched: number;
  user_note: string | null;
  last_click_time: string | null;
}

// 獲取用戶影片庫
export async function getUserVideos(channelId?: string): Promise<Video[]> {
  const params = channelId ? `?channel_id=${channelId}` : '';
  return apiRequest<Video[]>(`/api/video/list${params}`);
}

// 生成影片摘要
export async function generateSummary(videoId: string): Promise<{
  video_id: string;
  summary_status: number;
  summary_content: string | null;
  message: string | null;
  estimated_wait_seconds: number | null;
}> {
  return apiRequest('/api/video/summary', {
    method: 'POST',
    body: JSON.stringify({ video_id: videoId }),
  });
}

// 切換收藏狀態
export async function toggleFavorite(videoId: string): Promise<{
  message: string;
  video_id: string;
  is_favorite: number;
}> {
  return apiRequest(`/api/video/favorite/${videoId}`, {
    method: 'POST',
  });
}

// 儲存影片筆記
export async function saveVideoNote(videoId: string, note: string): Promise<{
  message: string;
  video_id: string;
  user_note: string;
}> {
  return apiRequest(`/api/video/note/${videoId}`, {
    method: 'PUT',
    body: JSON.stringify({ note }),
  });
}

// ============ 用戶相關 API ============

export interface User {
  user_no: number;
  account: string;
  user_status: number;
  membership_level: number;
  create_time: string;
}

// 獲取當前用戶資訊
export async function getCurrentUser(): Promise<User> {
  return apiRequest<User>('/api/user/me');
}

// ============ 認證相關 API ============

export interface LoginResponse {
  access_token: string;
  token_type: string;
}

// Google 登入
export async function googleLogin(googleToken: string): Promise<LoginResponse> {
  const response = await fetch(`${API_BASE_URL}/api/auth/google-login`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ google_token: googleToken }),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Login failed' }));
    throw new Error(error.detail || 'Login failed');
  }

  return response.json();
}

// 登出
export function logout() {
  if (typeof window !== 'undefined') {
    localStorage.removeItem('access_token');
  }
}

// 從 JWT Token 解析用戶信息
export function getUserInfoFromToken(): { email: string; picture?: string } | null {
  const token = getAuthToken();
  if (!token) return null;

  try {
    // JWT 格式: header.payload.signature
    const payload = token.split('.')[1];
    const decoded = JSON.parse(atob(payload));
    return {
      email: decoded.sub || decoded.email || 'User',
      picture: decoded.picture
    };
  } catch (error) {
    console.error('解析 Token 失敗:', error);
    return null;
  }
}

// 檢查 Token 是否過期
export function isTokenExpired(): boolean {
  const token = getAuthToken();
  if (!token) return true;

  try {
    const payload = token.split('.')[1];
    const decoded = JSON.parse(atob(payload));
    const exp = decoded.exp;

    if (!exp) return false;

    // exp 是秒級時間戳，Date.now() 是毫秒級
    return Date.now() >= exp * 1000;
  } catch (error) {
    console.error('檢查 Token 過期失敗:', error);
    return true;
  }
}

// ============ 使用者設定相關 API (新版 - tb_user_setting) ============

export interface UserSetting {
  user_no: number;
  // 通知相關
  notify_enable: number;  // 0:全關, 1:全開
  notify_interval: number;  // 通知間隔（分鐘）
  enable_line: number;  // 0:關, 1:開
  enable_email: number;  // 0:關, 1:開
  // AI 摘要相關
  ai_summary_length: number;  // 期望字數
  ai_tone: string;  // professional, humorous, friendly, concise, critical, encouraging
  ai_persona: string;  // general, engineer, teacher, investor, critic, summarizer
  // 系統欄位
  updated_at: string;
}

export interface AiOption {
  value: string;
  label: string;
}

export interface AiOptions {
  tones: AiOption[];
  personas: AiOption[];
  summary_length_options: number[];
  notify_interval_options: number[];
}

// 獲取使用者完整設定
export async function getUserSetting(): Promise<UserSetting> {
  return apiRequest<UserSetting>('/api/config/user/setting');
}

// 更新使用者設定（部分更新）
export async function updateUserSetting(settings: Partial<Omit<UserSetting, 'user_no' | 'updated_at'>>): Promise<UserSetting> {
  return apiRequest<UserSetting>('/api/config/user/setting', {
    method: 'PUT',
    body: JSON.stringify(settings),
  });
}

// 獲取 AI 選項列表
export async function getAiOptions(): Promise<AiOptions> {
  return apiRequest<AiOptions>('/api/config/ai-options');
}

// ============ LINE 綁定相關 API ============

export interface LineBindingToken {
  token: string;
  deep_link: string;
  expires_in: number;
  instructions: string[];
}

export interface LineBindingStatus {
  is_bound: boolean;
  line_user_id: string | null;
}

// 生成 LINE 綁定 Token
export async function generateLineBindingToken(): Promise<LineBindingToken> {
  return apiRequest<LineBindingToken>('/api/line/generate-binding-token', {
    method: 'POST',
  });
}

// 查詢 LINE 綁定狀態
export async function getLineBindingStatus(): Promise<LineBindingStatus> {
  return apiRequest<LineBindingStatus>('/api/line/binding-status');
}

// 解除 LINE 綁定
export async function unbindLine(): Promise<{ status: string; message: string }> {
  return apiRequest('/api/line/unbind', {
    method: 'POST',
  });
}

// ============ 舊版 API (準備廢棄) ============

export interface SystemParam {
  param_no: number;
  sort: number;
  caption: string;
  value: string;
}

export interface UserConfigItem {
  param_no: number;
  caption: string;
  value: number; // 0:關閉, 1:開啟
}

// 獲取系統參數列表（通知方式）
export async function getSystemParams(): Promise<SystemParam[]> {
  return apiRequest<SystemParam[]>('/api/config/params');
}

// 獲取使用者通知設定
export async function getUserConfigs(): Promise<UserConfigItem[]> {
  return apiRequest<UserConfigItem[]>('/api/config/user');
}

// 更新使用者通知設定
export async function updateUserConfig(paramValue: string, enabled: boolean): Promise<{
  message: string;
  param_value: string;
  enabled: boolean;
}> {
  return apiRequest('/api/config/user', {
    method: 'POST',
    body: JSON.stringify({ param_value: paramValue, enabled }),
  });
}
