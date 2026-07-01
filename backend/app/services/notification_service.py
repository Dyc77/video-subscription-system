import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import settings
from typing import List, Dict
import logging
import markdown

logger = logging.getLogger(__name__)


class NotificationService:
    """通知服務 - Email 發送"""

    def __init__(self):
        """初始化 Email 設定"""
        self.smtp_server = settings.SMTP_SERVER
        self.smtp_port = settings.SMTP_PORT
        self.smtp_user = settings.SMTP_USER
        self.smtp_password = settings.SMTP_PASSWORD
        self.from_email = settings.FROM_EMAIL

    def send_new_videos_notification(
        self,
        to_email: str,
        user_name: str,
        new_videos: List[Dict[str, str]],
        membership_level: int = 0
    ) -> bool:
        """
        發送新影片通知 Email

        Args:
            to_email: 收件人 Email
            user_name: 使用者名稱
            new_videos: 新影片列表
                [{
                    "channel_title": "頻道名稱",
                    "video_title": "影片標題",
                    "video_url": "影片連結",
                    "thumbnail_url": "縮圖連結",
                    "summary": "AI 摘要 (僅高級會員)"
                }, ...]
            membership_level: 會員等級 (0:免費, 1:付費)

        Returns:
            bool: 發送成功返回 True
        """
        try:
            # 構建 HTML Email 內容
            html_content = self._build_email_html(user_name, new_videos, membership_level)

            # 建立 Email
            message = MIMEMultipart("alternative")
            message["Subject"] = f"📺 您訂閱的頻道有 {len(new_videos)} 部新影片！"
            message["From"] = self.from_email
            message["To"] = to_email

            # 添加 HTML 內容
            html_part = MIMEText(html_content, "html")
            message.attach(html_part)

            # 發送 Email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(message)

            logger.info(f"成功發送通知給 {to_email}，包含 {len(new_videos)} 部新影片")
            return True

        except Exception as e:
            logger.error(f"發送 Email 失敗: {str(e)}")
            return False

    def _extract_video_id(self, video_url: str) -> str:
        """從 YouTube URL 中提取 video_id"""
        import re
        match = re.search(r'(?:v=|/)([a-zA-Z0-9_-]{11})', video_url)
        return match.group(1) if match else ""

    def _markdown_to_plain_text(self, md: str) -> str:
        """
        把摘要 markdown 轉為適合 <pre> 區塊呈現的純文字：
        - 移除 #、## 等 heading 前綴
        - 移除 **bold** 的星號
        - 把 [text](url) 改寫成「text (url)」讓 email client 能 auto-linkify URL
        - 收斂多餘的空行
        """
        import re
        text = re.sub(r'^#+\s+', '', md, flags=re.MULTILINE)
        text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'\1 (\2)', text)
        text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()

    def _convert_youtube_links_to_watch_page(self, summary_text: str, video_id: str) -> str:
        """
        將摘要中的 YouTube 時間戳記連結轉換為網站公開播放頁面連結

        Args:
            summary_text: 包含 YouTube 連結的摘要文字
            video_id: 影片 ID

        Returns:
            str: 轉換後的摘要文字
        """
        import re

        # 將 YouTube 連結 (https://www.youtube.com/watch?v=VIDEO_ID&t=XXXs)
        # 轉換為網站連結 (FRONTEND_URL/watch/VIDEO_ID?t=XXXs)
        def replace_youtube_link(match):
            timestamp_text = match.group(1)  # 時間戳記文字（例如：00:00）
            timestamp_link = match.group(2)  # 原始連結
            description = match.group(3)     # 描述文字

            # 提取時間參數
            time_match = re.search(r'[?&]t=(\d+)s?', timestamp_link)
            if time_match:
                seconds = time_match.group(1)
                # 生成網站連結（注意：使用 ? 而不是 &，因為是第一個參數）
                watch_link = f"{settings.FRONTEND_URL}/watch/{video_id}?t={seconds}"
                return f"- [{timestamp_text}]({watch_link}) {description}"

            return match.group(0)  # 如果沒有時間參數，保持原樣

        # 匹配格式：- [時間](YouTube連結) 描述
        pattern = r'^- \[([^\]]+)\]\((https://www\.youtube\.com/watch\?v=[^)]+)\)\s+(.+)$'

        lines = summary_text.split('\n')
        converted_lines = []

        for line in lines:
            match = re.match(pattern, line)
            if match:
                converted_lines.append(replace_youtube_link(match))
            else:
                converted_lines.append(line)

        return '\n'.join(converted_lines)

    def _build_email_html(self, user_name: str, new_videos: List[Dict[str, str]], membership_level: int = 0) -> str:
        """
        構建 Email HTML 內容

        Args:
            user_name: 使用者名稱
            new_videos: 新影片列表
            membership_level: 會員等級

        Returns:
            str: HTML 內容
        """
        # 按頻道分組
        videos_by_channel = {}
        for video in new_videos:
            channel = video["channel_title"]
            if channel not in videos_by_channel:
                videos_by_channel[channel] = []
            videos_by_channel[channel].append(video)

        # 構建影片列表 HTML
        videos_html = ""
        for channel_title, videos in videos_by_channel.items():
            videos_html += f"""
            <div style="margin-bottom: 30px;">
                <h3 style="color: #1f2937; font-size: 18px; margin-bottom: 15px; border-bottom: 2px solid #e5e7eb; padding-bottom: 8px;">
                    📢 {channel_title} ({len(videos)} 部新影片)
                </h3>
            """

            for video in videos:
                # 提取 video_id 並建立公開播放頁面連結
                video_id = self._extract_video_id(video['video_url'])
                watch_url = f"{settings.FRONTEND_URL}/watch/{video_id}" if video_id else video['video_url']

                # 判斷是否顯示摘要（高級會員專屬）
                summary_html = ""
                if video.get('summary'):
                    # 將 YouTube 時間戳記連結轉換為網站連結（仍維持 markdown 內部 link 格式）
                    summary_md = self._convert_youtube_links_to_watch_page(
                        video['summary'],
                        video_id
                    )

                    # 將 markdown 轉為純文字（保留換行與項目符號，但去除 ## ** [](url) 等語法）
                    summary_plain = self._markdown_to_plain_text(summary_md)

                    summary_html = f"""
                    <div style="margin-top: 15px; border-top: 1px solid #e5e7eb; padding-top: 12px;">
                        <p style="margin: 0 0 8px 0; font-size: 13px; color: #6b7280; font-weight: bold;">
                            💡 AI 完整摘要（Premium 會員專屬）
                        </p>
                        <pre style="margin: 0; font-family: inherit; font-size: 14px; color: #1f2937; line-height: 1.7; white-space: pre-wrap; word-wrap: break-word;">{summary_plain}</pre>
                    </div>
                    """
                elif membership_level == 0:
                    # 免費會員提示升級
                    summary_html = """
                    <div style="margin-top: 10px; padding: 10px; background-color: #e5e7eb; border-left: 3px solid #6b7280; border-radius: 4px;">
                        <p style="margin: 0; font-size: 13px; color: #374151;">
                            🔒 升級 Premium 會員即可自動收到 AI 摘要重點
                        </p>
                    </div>
                    """

                videos_html += f"""
                <div style="margin-bottom: 20px; padding: 15px; background-color: #f9fafb; border-radius: 8px; border-left: 4px solid #3b82f6;">
                    <div style="display: flex; align-items: start; gap: 15px;">
                        <img src="{video['thumbnail_url']}" alt="{video['video_title']}"
                             style="width: 160px; height: 90px; object-fit: cover; border-radius: 4px;" />
                        <div style="flex: 1;">
                            <h4 style="margin: 0 0 8px 0; font-size: 16px; color: #1f2937;">
                                <a href="{watch_url}"
                                   style="color: #1f2937; text-decoration: none; hover: color: #3b82f6;">
                                    {video['video_title']}
                                </a>
                            </h4>
                            <a href="{watch_url}"
                               style="display: inline-block; margin-top: 8px; padding: 8px 16px; background-color: #3b82f6; color: white; text-decoration: none; border-radius: 4px; font-size: 14px;">
                                立即觀看 →
                            </a>
                        </div>
                    </div>
                    {summary_html}
                </div>
                """

            videos_html += "</div>"

        # 完整 HTML 模板
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="margin: 0; padding: 0; font-family: Arial, sans-serif; background-color: #f3f4f6;">
            <div style="max-width: 600px; margin: 0 auto; background-color: white; padding: 30px;">
                <!-- Header -->
                <div style="text-align: center; margin-bottom: 30px;">
                    <h1 style="color: #1f2937; font-size: 24px; margin: 0 0 10px 0;">
                        📺 VideoHub 新影片通知
                    </h1>
                    <p style="color: #6b7280; font-size: 14px; margin: 0;">
                        Hi {user_name}，您訂閱的頻道有新影片了！
                    </p>
                </div>

                <!-- Videos List -->
                {videos_html}

                <!-- Footer -->
                <div style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #e5e7eb; text-align: center;">
                    <p style="color: #6b7280; font-size: 12px; margin: 0 0 10px 0;">
                        這是一封自動發送的通知郵件，請勿直接回覆。
                    </p>
                    <p style="color: #6b7280; font-size: 12px; margin: 0;">
                        如需調整通知設定，請前往
                        <a href="{settings.FRONTEND_URL}/dashboard/settings" style="color: #3b82f6;">設定頁面</a>
                    </p>
                </div>
            </div>
        </body>
        </html>
        """

        return html


# 創建全局實例
notification_service = NotificationService()
