"""
LINE 訊息發送服務
"""
from linebot.v3 import WebhookHandler
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    TextMessage,
    FlexMessage,
    FlexBubble,
    FlexBox,
    FlexText,
    FlexImage,
    FlexButton,
    URIAction,
    FlexCarousel
)
from app.core.config import settings
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)


class LineMessageService:
    """LINE 訊息發送服務"""

    def __init__(self):
        """初始化 LINE API 設定"""
        self.configuration = Configuration(
            access_token=settings.LINE_CHANNEL_ACCESS_TOKEN
        )
        self.api_client = ApiClient(self.configuration)
        self.messaging_api = MessagingApi(self.api_client)

    def send_new_videos_notification(
        self,
        line_user_id: str,
        user_name: str,
        new_videos: List[Dict[str, str]],
        membership_level: int = 0
    ) -> bool:
        """
        發送新影片通知到 LINE

        Args:
            line_user_id: LINE 使用者 ID
            user_name: 使用者名稱
            new_videos: 新影片列表
            membership_level: 會員等級

        Returns:
            bool: 發送成功返回 True
        """
        try:
            # 按頻道分組
            videos_by_channel = {}
            for video in new_videos:
                channel = video["channel_title"]
                if channel not in videos_by_channel:
                    videos_by_channel[channel] = []
                videos_by_channel[channel].append(video)

            # 建立 Flex Message 泡泡（最多 12 個）
            bubbles = []
            video_count = 0

            for channel_title, videos in videos_by_channel.items():
                for video in videos[:12 - video_count]:  # LINE 限制最多 12 個 bubble
                    bubble = self._create_video_bubble(
                        video=video,
                        membership_level=membership_level
                    )
                    bubbles.append(bubble)
                    video_count += 1

                    if video_count >= 12:
                        break

                if video_count >= 12:
                    break

            # 建立 Flex Carousel
            flex_carousel = FlexCarousel(contents=bubbles)

            # 建立 Flex Message
            flex_message = FlexMessage(
                alt_text=f"📺 您訂閱的頻道有 {len(new_videos)} 部新影片！",
                contents=flex_carousel
            )

            # 發送訊息
            from linebot.v3.messaging import PushMessageRequest
            request = PushMessageRequest(
                to=line_user_id,
                messages=[flex_message]
            )

            self.messaging_api.push_message(request)

            logger.info(f"成功發送 LINE 通知給 {line_user_id}，包含 {len(bubbles)} 部影片")
            return True

        except Exception as e:
            logger.error(f"發送 LINE 訊息失敗: {str(e)}")
            return False

    def _extract_video_id(self, video_url: str) -> str:
        """從 YouTube URL 中提取 video_id"""
        import re
        match = re.search(r'(?:v=|/)([a-zA-Z0-9_-]{11})', video_url)
        return match.group(1) if match else ""

    def _create_video_bubble(
        self,
        video: Dict[str, str],
        membership_level: int = 0
    ) -> FlexBubble:
        """
        建立單個影片的 Flex Bubble

        Args:
            video: 影片資訊
            membership_level: 會員等級

        Returns:
            FlexBubble: Flex Message 泡泡
        """
        # 提取 video_id 並建立公開播放頁面連結
        from app.core.config import settings
        video_id = self._extract_video_id(video['video_url'])
        watch_url = f"{settings.FRONTEND_URL}/watch/{video_id}" if video_id else video['video_url']

        # 縮圖
        hero = FlexImage(
            url=video['thumbnail_url'],
            size="full",
            aspect_ratio="20:13",
            aspect_mode="cover"
        )

        # 頻道名稱 + 影片標題
        body_contents = [
            FlexText(
                text=video['channel_title'],
                size="sm",
                color="#999999",
                weight="bold"
            ),
            FlexText(
                text=video['video_title'],
                size="md",
                weight="bold",
                wrap=True,
                max_lines=2
            )
        ]

        # VIP 摘要（如果有）
        if video.get('summary') and membership_level == 1:
            import re
            summary_text = video['summary']

            # 提取「一句話總結」
            one_liner = ""
            one_line_match = re.search(r'## 📝 一句話總結\s*\n(.+?)(?=\n##|$)', summary_text, re.DOTALL)
            if one_line_match:
                one_liner = one_line_match.group(1).strip()

            # 提取「重點摘要」（前 3 個重點）
            key_points = []
            key_points_match = re.search(r'## 🎯 重點摘要\s*\n((?:- .+\n?)+)', summary_text, re.DOTALL)
            if key_points_match:
                points_text = key_points_match.group(1)
                all_points = re.findall(r'- (.+)', points_text)
                # 只取前 3 個重點，每個最多 40 字
                key_points = [p[:40] + "..." if len(p) > 40 else p for p in all_points[:3]]

            # 組合預覽文字
            preview_parts = []
            if one_liner:
                preview_parts.append(f"📌 {one_liner}")
            if key_points:
                preview_parts.append("\n\n🎯 重點:")
                for i, point in enumerate(key_points, 1):
                    preview_parts.append(f"\n{i}. {point}")

            summary_preview = "".join(preview_parts) if preview_parts else summary_text[:200]

            # 限制最多 300 字
            if len(summary_preview) > 300:
                summary_preview = summary_preview[:300] + "..."

            body_contents.append(
                FlexBox(
                    layout="vertical",
                    margin="lg",
                    spacing="sm",
                    background_color="#FEF3C7",
                    padding_all="10px",
                    corner_radius="4px",
                    contents=[
                        FlexText(
                            text="💡 AI 摘要預覽",
                            size="xs",
                            color="#92400E",
                            weight="bold"
                        ),
                        FlexText(
                            text=summary_preview,
                            size="xs",
                            color="#78350F",
                            wrap=True,
                            max_lines=6
                        )
                    ]
                )
            )
        elif membership_level == 0:
            # 免費會員提示
            body_contents.append(
                FlexBox(
                    layout="vertical",
                    margin="lg",
                    spacing="sm",
                    background_color="#E5E7EB",
                    padding_all="10px",
                    corner_radius="4px",
                    contents=[
                        FlexText(
                            text="🔒 升級 Premium 即可看 AI 摘要",
                            size="xs",
                            color="#374151",
                            wrap=True
                        )
                    ]
                )
            )

        body = FlexBox(
            layout="vertical",
            spacing="md",
            contents=body_contents
        )

        # 按鈕
        footer = FlexBox(
            layout="vertical",
            spacing="sm",
            contents=[
                FlexButton(
                    style="primary",
                    action=URIAction(
                        label="立即觀看",
                        uri=watch_url
                    )
                )
            ]
        )

        return FlexBubble(
            hero=hero,
            body=body,
            footer=footer
        )

    def send_binding_success_message(self, line_user_id: str, user_name: str) -> bool:
        """
        發送綁定成功訊息

        Args:
            line_user_id: LINE 使用者 ID
            user_name: 使用者名稱

        Returns:
            bool: 發送成功返回 True
        """
        try:
            from linebot.v3.messaging import PushMessageRequest

            message = TextMessage(
                text=f"🎉 綁定成功！\n\n"
                     f"Hi {user_name}，您的帳號已成功綁定 LINE 通知！\n\n"
                     f"現在當您訂閱的頻道有新影片時，我們會透過 LINE 通知您。\n\n"
                     f"📌 提醒：您可以隨時在設定頁面關閉 LINE 通知或解除綁定。"
            )

            request = PushMessageRequest(
                to=line_user_id,
                messages=[message]
            )

            self.messaging_api.push_message(request)
            logger.info(f"成功發送綁定成功訊息給 {line_user_id}")
            return True

        except Exception as e:
            logger.error(f"發送綁定成功訊息失敗: {str(e)}")
            return False


# 創建全局實例
line_message_service = LineMessageService()
