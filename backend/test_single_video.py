"""測試單一影片的字幕"""
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound

video_id = "Edvqt7IgHYo"

print(f"測試影片 ID: {video_id}")
print("=" * 60)

try:
    transcript_data = YouTubeTranscriptApi.get_transcript(video_id, languages=['en'])
    print(f"✅ 找到英文字幕！共 {len(transcript_data)} 條目")

    # 顯示前幾條
    for i, entry in enumerate(transcript_data[:5]):
        print(f"{i+1}. [{entry['start']:.1f}s] {entry['text']}")

except Exception as e:
    print(f"❌ 錯誤: {e}")
    print("\n嘗試列出所有可用字幕...")
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        for t in transcript_list:
            print(f"  - {t.language} ({t.language_code})")
    except Exception as e2:
        print(f"❌ 無法列出字幕: {e2}")
