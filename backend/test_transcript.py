"""
測試 YouTube Transcript API 功能
"""
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound

def test_transcript(video_id: str):
    """測試取得 YouTube 字幕"""
    print("=" * 60)
    print(f"🧪 測試影片 ID: {video_id}")
    print("=" * 60)

    try:
        # 列出所有可用的字幕
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        print("✅ 成功取得字幕列表")

        # 顯示所有可用的字幕語言
        print("\n📝 可用的字幕語言:")
        for transcript in transcript_list:
            print(f"  - {transcript.language} ({transcript.language_code}) - {'自動生成' if transcript.is_generated else '手動'}")

        # 嘗試取得繁體中文字幕
        preferred_languages = ['zh-TW', 'zh-Hant', 'zh-CN', 'zh-Hans', 'en']

        transcript = None
        for lang in preferred_languages:
            try:
                transcript = transcript_list.find_transcript([lang])
                print(f"\n✅ 找到偏好語言字幕: {lang}")
                break
            except:
                continue

        # 如果沒找到偏好語言，取第一個可用的
        if not transcript:
            transcript = list(transcript_list)[0]
            print(f"\n📝 使用第一個可用字幕: {transcript.language}")

        # 取得字幕內容（使用備用方法）
        try:
            transcript_data = transcript.fetch()
        except Exception as fetch_error:
            print(f"⚠️ fetch() 失敗: {fetch_error}")
            # 嘗試直接使用 YouTubeTranscriptApi.get_transcript
            print("🔄 嘗試使用備用方法...")
            transcript_data = YouTubeTranscriptApi.get_transcript(video_id, languages=[transcript.language_code])

        # 組合成完整文字
        full_text = ' '.join([entry['text'] for entry in transcript_data])

        print(f"\n✅ 字幕長度: {len(full_text)} 字元")
        print(f"\n📄 字幕預覽 (前 500 字元):")
        print(full_text[:500])
        print("=" * 60)

        return True

    except TranscriptsDisabled:
        print("❌ 此影片沒有開啟字幕功能")
        print("💡 需要使用音訊下載 Fallback")
        print("=" * 60)
        return False

    except NoTranscriptFound:
        print("❌ 找不到任何字幕")
        print("💡 需要使用音訊下載 Fallback")
        print("=" * 60)
        return False

    except Exception as e:
        print(f"❌ 錯誤: {str(e)}")
        print("💡 需要使用音訊下載 Fallback")
        print("=" * 60)
        return False


if __name__ == "__main__":
    # 測試幾個不同的影片
    test_videos = [
        "dQw4w9WgXcQ",  # Rick Astley - Never Gonna Give You Up (應該有字幕)
        "jNQXAC9IVRw",  # Me at the zoo (YouTube 第一支影片，可能沒字幕)
    ]

    for video_id in test_videos:
        result = test_transcript(video_id)
        print(f"結果: {'✅ 有字幕' if result else '❌ 無字幕，需要 Fallback'}\n")
