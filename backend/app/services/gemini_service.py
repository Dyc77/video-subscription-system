import os
import time
import base64
import tempfile
import google.generativeai as genai
import yt_dlp
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class GeminiService:
    """Gemini API 服務類 - Direct URL 主路徑、音訊下載 fallback"""

    def __init__(self, config_settings=None):
        """初始化 Gemini API"""
        # 允許傳入自訂 settings（用於子進程重新載入設定）
        if config_settings is None:
            config_settings = settings

        self.settings = config_settings
        self.api_key = config_settings.GOOGLE_API_KEY
        self.model = config_settings.GEMINI_MODEL
        genai.configure(api_key=self.api_key)

    def generate_summary_from_url(self, youtube_url: str, video_id: str) -> str:
        """
        從 YouTube 影片生成摘要（智能 Fallback Pipeline）

        Pipeline 流程：
        1. 優先嘗試 Gemini 直接分析 YouTube URL（fileData/file_uri，免下載）
        2. 失敗時降級用 yt-dlp 下載音訊 + Gemini File API（需要 cookies）

        Args:
            youtube_url: YouTube 影片完整 URL
            video_id: YouTube 影片 ID

        Returns:
            str: Markdown 格式的摘要內容
        """
        # 測試模式：用 60 秒等待取代 Gemini API 呼叫
        if self.settings.TEST_MODE:
            print("=" * 60)
            print("🧪 測試模式啟動：模擬 Gemini API 延遲 60 秒")
            print(f"📹 Video ID: {video_id}")
            print(f"🔗 YouTube URL: {youtube_url}")
            print("⏳ 開始等待 60 秒...")
            time.sleep(60)
            print("✅ 測試模式完成，返回測試摘要內容")
            print("=" * 60)

            # 返回測試用摘要內容
            return """## 📝 一句話總結
這是測試模式的摘要內容，用於測試 multiprocessing 功能。

## 🎯 重點摘要
- 測試重點 1
- 測試重點 2
- 測試重點 3

## ⏱️ 時間軸導覽
- 00:00 測試開場
- 01:00 測試內容
- 02:00 測試結尾

## 💡 關鍵洞察
這是測試模式，實際使用時請關閉 TEST_MODE。"""

        print("=" * 60)
        print(f"🎬 開始生成 YouTube 影片摘要")
        print(f"📹 Video ID: {video_id}")
        print(f"🔗 YouTube URL: {youtube_url}")
        print(f"🤖 使用模型: {self.model}")

        try:
            summary_text = self._generate_summary_from_youtube_url(youtube_url, video_id)
        except Exception as e:
            print(f"⚠️ Direct URL 失敗，降級到音訊下載：{e}")
            summary_text = self._generate_summary_from_audio(youtube_url, video_id)

        # 統一在外層轉換時間戳記為可點擊連結
        summary_text = self._convert_timestamps_to_links(summary_text, youtube_url)
        print("=" * 60)

        return summary_text

    def _generate_summary_from_youtube_url(self, youtube_url: str, video_id: str) -> str:
        """
        直接把 YouTube URL 傳給 Gemini 分析（無需下載、無需 cookies）

        Gemini 2.x 支援透過 fileData (file_uri + mime_type="video/*") 直接讀取
        公開 YouTube 影片，由 Google 後端抓取與處理。

        Args:
            youtube_url: YouTube 影片完整 URL
            video_id: YouTube 影片 ID

        Returns:
            str: Markdown 格式的摘要內容（未經時間戳記轉換）
        """
        print("🌐 嘗試使用 Gemini 直接分析 YouTube URL（無需下載）")
        model = genai.GenerativeModel(self.model)
        prompt = self._build_summary_prompt()

        response = model.generate_content([
            {"file_data": {"file_uri": youtube_url, "mime_type": "video/*"}},
            prompt,
        ])

        summary_text = response.text
        print(f"✅ Direct URL 摘要生成完成 ({len(summary_text)} 字元)")
        return summary_text

    def _generate_summary_from_audio(self, youtube_url: str, video_id: str) -> str:
        """
        從 YouTube 影片音訊生成摘要（下載音訊 + 上傳至 Gemini File API）

        使用 yt-dlp 下載音訊，然後上傳到 Gemini 進行分析

        Args:
            youtube_url: YouTube 影片完整 URL
            video_id: YouTube 影片 ID

        Returns:
            str: Markdown 格式的摘要內容（未經時間戳記轉換）
        """
        print("🎬 使用 Gemini File API 分析音訊")

        # 設定暫存檔名（使用 timestamp 防止檔名衝突）
        temp_filename = f"temp_audio_{video_id}_{int(time.time())}.m4a"
        temp_filepath = os.path.join("temp", temp_filename)

        # 確保 temp 目錄存在
        os.makedirs("temp", exist_ok=True)

        try:
            # --- 步驟 1: 下載音訊 (極致省空間模式: 只抓音訊) ---
            print("📥 正在擷取音訊軌 (Audio Only)...")

            ydl_opts = {
                'format': 'bestaudio[ext=m4a]/bestaudio',  # 優先 m4a 格式的音訊，否則最佳音訊
                'outtmpl': temp_filepath,     # 暫存檔名
                'quiet': True,                # 安靜模式
                'no_warnings': True,
                'overwrites': True,
            }

            # 處理 YouTube Cookies 認證（避免 bot 檢測）
            cookies_file_path = None
            temp_cookies_file = None

            try:
                # 優先使用環境變數中的 Base64 編碼 cookies
                if self.settings.YOUTUBE_COOKIES_BASE64:
                    print("🍪 使用環境變數中的 cookies (Base64)")
                    # 解碼 Base64
                    cookies_content = base64.b64decode(self.settings.YOUTUBE_COOKIES_BASE64).decode('utf-8')
                    # 建立暫存檔案
                    temp_cookies_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt')
                    temp_cookies_file.write(cookies_content)
                    temp_cookies_file.close()
                    cookies_file_path = temp_cookies_file.name
                    ydl_opts['cookiefile'] = cookies_file_path
                # 否則檢查是否有本地 cookies.txt 檔案
                else:
                    local_cookies_path = os.path.join(os.path.dirname(__file__), '..', '..', 'cookies.txt')
                    if os.path.exists(local_cookies_path):
                        print("🍪 使用本地 cookies.txt 進行認證")
                        ydl_opts['cookiefile'] = local_cookies_path
                    else:
                        print("⚠️ 未找到 cookies，可能會遇到 YouTube bot 檢測問題")
                        print("💡 提示：請設定 YOUTUBE_COOKIES_BASE64 環境變數或放置 cookies.txt 檔案")

                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([youtube_url])

            finally:
                # 清理暫存 cookies 檔案
                if temp_cookies_file and os.path.exists(temp_cookies_file.name):
                    try:
                        os.unlink(temp_cookies_file.name)
                    except Exception as e:
                        logger.warning(f"清理暫存 cookies 檔案失敗: {e}")

            file_size_mb = os.path.getsize(temp_filepath) / (1024 * 1024)
            print(f"✅ 下載完成，檔案大小: {file_size_mb:.2f} MB")

            # --- 步驟 2: 上傳到 Gemini (File API) ---
            print("☁️ 正在上傳到 Gemini...")
            myfile = genai.upload_file(temp_filepath)

            # 等待 Google 處理檔案
            while myfile.state.name == "PROCESSING":
                time.sleep(1)
                myfile = genai.get_file(myfile.name)

            print(f"✅ 檔案已上傳: {myfile.name}")

            # --- 步驟 3: 呼叫 AI 生成摘要 ---
            print("🤖 AI 正在分析...")
            model = genai.GenerativeModel(self.model)

            prompt = self._build_summary_prompt()

            response = model.generate_content([myfile, prompt])

            # --- 步驟 4: 清理雲端檔案 ---
            genai.delete_file(myfile.name)

            summary_text = response.text
            print(f"✅ 摘要生成完成 ({len(summary_text)} 字元)")

            return summary_text

        except Exception as e:
            print(f"❌ 音訊路徑生成摘要失敗！錯誤: {str(e)}")
            raise Exception(f"生成摘要失敗: {str(e)}")

        finally:
            # --- 清理本地檔案 ---
            if os.path.exists(temp_filepath):
                os.remove(temp_filepath)

    def _build_summary_prompt(self) -> str:
        """
        建立影片摘要生成的提示詞

        Returns:
            str: 完整的提示詞
        """
        prompt = """# Role
你是一位專業的影音內容分析師，擅長分析 YouTube 影片的內容、結構和重點。

# Task
請仔細觀看這部 YouTube 影片，然後生成一份結構化的摘要報告。

# Output Format（使用繁體中文 Markdown）

## 📝 一句話總結
[用一句話精準概括這部影片的核心主題和價值]

## 🎯 重點摘要
- [重點 1 - 包含具體細節]
- [重點 2 - 包含具體細節]
- [重點 3 - 包含具體細節]
- [重點 4 - 包含具體細節]
- [更多重點...]

## ⏱️ 時間軸導覽
- 00:00 開場與主題介紹
- XX:XX 第一個主要段落
- XX:XX 第二個主要段落
- XX:XX 重點討論或示範
- XX:XX 總結與結語

**重要：時間軸格式必須是「MM:SS 描述文字」，不要用方括號包時間！**

## 💡 關鍵洞察
[1-2 段文字，說明這部影片的核心價值、適合的觀眾群，以及主要收穫]

---

# Instructions
1. 請基於影片的**實際內容**生成摘要
2. 時間軸要盡量準確標註重要段落，格式：MM:SS 或 HH:MM:SS
3. 時間軸不要使用方括號 []，直接寫時間
4. 重點摘要要具體且可操作
5. 使用專業但易懂的語言
6. 保持客觀中立的分析態度

---

請開始分析並生成摘要："""

        return prompt

    def _convert_timestamps_to_links(self, summary_text: str, youtube_url: str) -> str:
        """
        將摘要中的時間戳記轉換為可點擊的 YouTube 連結

        Args:
            summary_text: 原始摘要文字
            youtube_url: YouTube 影片 URL

        Returns:
            str: 轉換後的摘要文字
        """
        import re

        # 提取 video_id
        video_id_match = re.search(r'(?:v=|/)([a-zA-Z0-9_-]{11})', youtube_url)
        if not video_id_match:
            return summary_text

        video_id = video_id_match.group(1)
        base_url = f"https://www.youtube.com/watch?v={video_id}"

        # 匹配時間戳記格式：HH:MM:SS 或 MM:SS 或 H:MM:SS
        # 只匹配行首的時間戳記（- 後面的）
        def replace_timestamp(match):
            timestamp = match.group(1)
            description = match.group(2)

            # 將時間轉換為秒數
            parts = timestamp.split(':')
            if len(parts) == 2:  # MM:SS
                seconds = int(parts[0]) * 60 + int(parts[1])
            elif len(parts) == 3:  # HH:MM:SS
                seconds = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
            else:
                return match.group(0)  # 不符合格式，保持原樣

            # 生成帶時間戳記的 YouTube 連結
            youtube_link = f"{base_url}&t={seconds}s"
            return f"- [{timestamp}]({youtube_link}) {description}"

        # 使用正則表達式替換
        # 匹配格式：- HH:MM:SS 描述 或 - MM:SS 描述
        pattern = r'^- (\d{1,2}:\d{2}(?::\d{2})?)\s+(.+)$'

        lines = summary_text.split('\n')
        converted_lines = []

        for line in lines:
            match = re.match(pattern, line)
            if match:
                converted_lines.append(replace_timestamp(match))
            else:
                converted_lines.append(line)

        return '\n'.join(converted_lines)


# 建立全域實例
gemini_service = GeminiService()
