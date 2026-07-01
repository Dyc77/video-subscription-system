from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound
import logging
import requests
import feedparser
from app.core.config import settings

logger = logging.getLogger(__name__)


class YouTubeService:
    """YouTube 服务类"""

    def get_transcript(self, video_id: str, languages: list = None) -> str:
        """
        获取YouTube影片字幕

        Args:
            video_id: YouTube 影片 ID
            languages: 优先语言列表，默认 ['zh-TW', 'zh-CN', 'zh', 'en']

        Returns:
            str: 字幕文本（带时间戳）

        Raises:
            Exception: 当无法获取字幕时抛出异常
        """
        if languages is None:
            languages = ['zh-TW', 'zh-CN', 'zh', 'en']

        logger.info(f"🎯 開始獲取字幕 | Video ID: {video_id}")
        logger.info(f"🌐 優先語言: {languages}")

        try:
            # 获取字幕列表
            logger.info("📋 正在獲取可用字幕列表...")
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            logger.info(f"✅ 成功獲取字幕列表")

            # 列出所有可用的字幕
            available_transcripts = []
            try:
                for transcript in transcript_list:
                    available_transcripts.append({
                        'language': transcript.language,
                        'language_code': transcript.language_code,
                        'is_generated': transcript.is_generated,
                        'is_translatable': transcript.is_translatable
                    })
                logger.info(f"📝 可用字幕: {available_transcripts}")
            except Exception as list_error:
                logger.warning(f"無法列出所有字幕: {str(list_error)}")

            # 尝试获取手动字幕
            transcript = None
            try:
                logger.info(f"🔍 嘗試獲取手動字幕 (語言: {languages})")
                transcript = transcript_list.find_manually_created_transcript(languages)
                logger.info(f"✅ 找到手動字幕: {transcript.language} ({transcript.language_code})")
            except NoTranscriptFound:
                logger.info("⚠️ 沒有找到手動字幕，嘗試自動生成的字幕...")
                # 如果没有手动字幕，尝试自动生成的字幕
                transcript = transcript_list.find_generated_transcript(languages)
                logger.info(f"✅ 找到自動生成字幕: {transcript.language} ({transcript.language_code})")

            # 获取字幕数据
            logger.info("📥 正在下載字幕數據...")
            transcript_data = transcript.fetch()
            logger.info(f"✅ 字幕下載完成，共 {len(transcript_data)} 個片段")

            # 格式化字幕（带时间戳）
            logger.info("🔄 正在格式化字幕...")
            formatted_transcript = self._format_transcript(transcript_data)
            logger.info(f"✅ 字幕格式化完成，總長度: {len(formatted_transcript)} 字元")

            return formatted_transcript

        except TranscriptsDisabled as e:
            logger.error("=" * 60)
            logger.error(f"❌ 字幕已被禁用！")
            logger.error(f"Video ID: {video_id}")
            logger.error(f"錯誤: {str(e)}")
            logger.error("=" * 60)
            raise Exception("此影片的字幕已被禁用")

        except NoTranscriptFound as e:
            logger.error("=" * 60)
            logger.error(f"❌ 沒有可用的字幕！")
            logger.error(f"Video ID: {video_id}")
            logger.error(f"請求的語言: {languages}")
            logger.error(f"錯誤: {str(e)}")
            logger.error("=" * 60)
            raise Exception("此影片没有可用的字幕")

        except Exception as e:
            logger.error("=" * 60)
            logger.error(f"❌ 獲取字幕時發生未知錯誤！")
            logger.error(f"Video ID: {video_id}")
            logger.error(f"錯誤類型: {type(e).__name__}")
            logger.error(f"錯誤訊息: {str(e)}")
            logger.error(f"完整錯誤: {repr(e)}")
            logger.error("=" * 60)
            raise Exception(f"获取字幕失败: {str(e)}")

    def _format_transcript(self, transcript_data: list) -> str:
        """
        格式化字幕数据

        Args:
            transcript_data: 字幕数据列表

        Returns:
            str: 格式化后的字幕文本
        """
        formatted_lines = []

        for entry in transcript_data:
            timestamp = self._format_timestamp(entry['start'])
            text = entry['text'].strip()
            formatted_lines.append(f"[{timestamp}] {text}")

        return "\n".join(formatted_lines)

    def _format_timestamp(self, seconds: float) -> str:
        """
        将秒数转换为 MM:SS 格式

        Args:
            seconds: 秒数

        Returns:
            str: MM:SS 格式的时间戳
        """
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes:02d}:{secs:02d}"

    def get_channel_info_from_url(self, channel_url: str) -> dict:
        """
        從 YouTube 頻道網址解析頻道資訊（使用 RSS，零 API Quota）

        支援的網址格式：
        - https://www.youtube.com/@channelhandle
        - https://www.youtube.com/channel/UCxxxxxx
        - https://www.youtube.com/c/CustomName

        Args:
            channel_url: YouTube 頻道網址

        Returns:
            dict: {
                'channel_id': str,
                'title': str,
                'thumbnail_url': str,
                'rss_url': str
            }
        """
        try:
            # 1. 從網址提取 channel_id
            channel_id = self._extract_channel_id(channel_url)

            # 2. 使用 RSS 獲取頻道資訊（零 Quota）
            rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"

            feed = feedparser.parse(rss_url)

            if not feed.entries and not feed.feed:
                raise Exception("無法解析頻道 RSS，請確認頻道網址是否正確")

            # 3. 從 RSS feed 中提取頻道資訊
            channel_title = feed.feed.get('title', 'Unknown Channel')

            # 4. 從頻道頁面抓取真實的頻道頭像（零 Quota）
            thumbnail_url = self._get_channel_thumbnail(channel_id)

            return {
                'channel_id': channel_id,
                'title': channel_title,
                'thumbnail_url': thumbnail_url,
                'rss_url': rss_url
            }

        except Exception as e:
            logger.error(f"獲取頻道資訊失敗: {str(e)}")
            raise Exception(f"獲取頻道資訊失敗: {str(e)}")

    def _extract_channel_id(self, channel_url: str) -> str:
        """
        從各種 YouTube 網址格式中提取 channel_id

        Args:
            channel_url: YouTube 頻道網址

        Returns:
            str: channel_id (UC開頭的24字元ID)
        """
        import re
        from urllib.parse import urlparse, parse_qs

        # 1. 清理網址：移除查詢參數（如 ?si=xxx）和片段（如 #xxx）
        parsed_url = urlparse(channel_url)
        # 重建乾淨的網址（只保留 scheme, netloc, path）
        clean_url = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}"
        # 移除網址結尾的斜線
        clean_url = clean_url.rstrip('/')

        logger.info(f"原始網址: {channel_url}")
        logger.info(f"清理後網址: {clean_url}")

        # 格式1: https://www.youtube.com/channel/UCxxxxxx (最直接)
        if '/channel/' in clean_url:
            channel_id = clean_url.split('/channel/')[-1]
            # 移除可能殘留的任何特殊字符
            channel_id = re.sub(r'[^a-zA-Z0-9_-]', '', channel_id)
            if channel_id.startswith('UC') and len(channel_id) == 24:
                logger.info(f"✅ 解析成功 (格式1 - 直接 channel_id): {channel_id}")
                return channel_id

        # 格式2: https://www.youtube.com/@channelhandle (需要轉換)
        if '/@' in clean_url:
            handle = clean_url.split('/@')[-1]
            # 移除可能殘留的任何特殊字符
            handle = re.sub(r'[^a-zA-Z0-9_-]', '', handle)
            logger.info(f"解析 @handle: {handle}")
            return self._get_channel_id_from_handle(handle)

        # 格式3: https://www.youtube.com/c/CustomName (需要轉換)
        if '/c/' in clean_url:
            custom_name = clean_url.split('/c/')[-1]
            # 移除可能殘留的任何特殊字符
            custom_name = re.sub(r'[^a-zA-Z0-9_-]', '', custom_name)
            logger.info(f"解析自訂名稱: {custom_name}")
            return self._get_channel_id_from_custom_name(custom_name)

        # 格式4: https://www.youtube.com/user/username (舊格式，需要轉換)
        if '/user/' in clean_url:
            username = clean_url.split('/user/')[-1]
            # 移除可能殘留的任何特殊字符
            username = re.sub(r'[^a-zA-Z0-9_-]', '', username)
            logger.info(f"解析使用者名稱: {username}")
            return self._get_channel_id_from_username(username)

        raise Exception(f"不支援的頻道網址格式: {channel_url}")

    def _extract_own_channel_id_from_html(self, html: str) -> str | None:
        """
        從 YouTube 頻道頁面 HTML 中精準提取「頁面自己的」channel_id

        YouTube 頻道頁的 HTML 裡會出現大量其他頻道的 ID（推薦、側邊欄、相關頻道等），
        所以不能用「第一個 UC... 字串」當答案 — 必須用只指向頁面自己頻道的 anchor。

        Returns:
            str | None: channel_id (UC...) 或 None（沒找到任何高信賴 anchor）
        """
        import re

        # 高信賴度 pattern — 只會匹配頁面本身的頻道
        anchored_patterns = [
            # RSS feed link（最可靠：YouTube 一定會在頁面 head 放這頁自己的 RSS）
            r'href="https?://www\.youtube\.com/feeds/videos\.xml\?channel_id=(UC[a-zA-Z0-9_-]{22})"',
            # og:url meta 指向 /channel/UC...
            r'<meta\s+property="og:url"\s+content="[^"]*?/channel/(UC[a-zA-Z0-9_-]{22})"',
            # canonical link 指向 /channel/UC...
            r'<link\s+rel="canonical"\s+href="[^"]*?/channel/(UC[a-zA-Z0-9_-]{22})"',
            # channelMetadataRenderer 區塊（頁面自身的 metadata）
            r'"channelMetadataRenderer":\s*\{[^{}]*?"externalId"\s*:\s*"(UC[a-zA-Z0-9_-]{22})"',
        ]

        for pattern in anchored_patterns:
            match = re.search(pattern, html)
            if match:
                return match.group(1)

        return None

    def _get_channel_id_from_handle(self, handle: str) -> str:
        """從 @handle 獲取 channel_id（通過抓取網頁）"""
        try:
            url = f"https://www.youtube.com/@{handle}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            channel_id = self._extract_own_channel_id_from_html(response.text)
            if channel_id:
                return channel_id

            raise Exception(f"無法從 @{handle} 解析 channel_id，請嘗試使用完整的頻道 ID 網址")
        except Exception as e:
            logger.error(f"解析 @handle 失敗: {str(e)}")
            raise Exception(f"解析頻道失敗: {str(e)}")

    def _get_channel_id_from_custom_name(self, custom_name: str) -> str:
        """從自訂頻道名稱獲取 channel_id"""
        try:
            url = f"https://www.youtube.com/c/{custom_name}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            channel_id = self._extract_own_channel_id_from_html(response.text)
            if channel_id:
                return channel_id

            raise Exception(f"無法從 /c/{custom_name} 解析 channel_id")
        except Exception as e:
            logger.error(f"解析自訂名稱失敗: {str(e)}")
            raise Exception(f"解析頻道失敗: {str(e)}")

    def _get_channel_id_from_username(self, username: str) -> str:
        """從舊版 username 獲取 channel_id"""
        try:
            url = f"https://www.youtube.com/user/{username}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            channel_id = self._extract_own_channel_id_from_html(response.text)
            if channel_id:
                return channel_id

            raise Exception(f"無法從 /user/{username} 解析 channel_id")
        except Exception as e:
            logger.error(f"解析使用者名稱失敗: {str(e)}")
            raise Exception(f"解析頻道失敗: {str(e)}")

    def _get_channel_thumbnail(self, channel_id: str) -> str:
        """
        從頻道頁面抓取真實的頻道頭像（零 API Quota）

        Args:
            channel_id: YouTube 頻道 ID

        Returns:
            str: 頻道頭像 URL
        """
        try:
            url = f"https://www.youtube.com/channel/{channel_id}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            import re
            # 嘗試從 HTML 中提取頻道頭像 URL
            # YouTube 頻道頭像通常在 og:image meta tag 或 JSON-LD 中

            # 模式1: og:image meta tag
            og_image_match = re.search(r'<meta property="og:image" content="([^"]+)"', response.text)
            if og_image_match:
                return og_image_match.group(1)

            # 模式2: 從 ytInitialData 中提取
            thumbnail_match = re.search(r'"avatar":\{"thumbnails":\[\{"url":"([^"]+)"', response.text)
            if thumbnail_match:
                thumbnail_url = thumbnail_match.group(1)
                # 確保使用 https
                if thumbnail_url.startswith('//'):
                    thumbnail_url = 'https:' + thumbnail_url
                return thumbnail_url

            # 模式3: 使用 YouTube 頻道頭像的標準格式
            # 格式: https://yt3.ggpht.com/ytc/[channel_id]
            logger.warning(f"無法從頁面提取頻道頭像，使用預設格式: {channel_id}")
            return f"https://yt3.ggpht.com/ytc/{channel_id}"

        except Exception as e:
            logger.warning(f"抓取頻道頭像失敗: {str(e)}，使用預設頭像")
            # 如果失敗，返回 YouTube 預設頻道頭像
            return "https://yt3.ggpht.com/ytc/default_channel_avatar.jpg"


# 创建全局实例
youtube_service = YouTubeService()
