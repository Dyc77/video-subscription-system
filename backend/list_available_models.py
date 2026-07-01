import google.generativeai as genai
import os
from dotenv import load_dotenv

# 載入 .env 檔案
load_dotenv()

# 請確保你的 API Key 已經設定在環境變數，或是直接填入下方
api_key = os.getenv("GOOGLE_API_KEY") # 或直接填 "AIza..."

if not api_key:
    print("❌ 錯誤：找不到 GOOGLE_API_KEY")
    print("請確認 .env 檔案中有設定 GOOGLE_API_KEY")
    exit(1)

genai.configure(api_key=api_key)

print("🔍 正在查詢你的 API Key 可用的模型清單...\n")

try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"- {m.name}")
except Exception as e:
    print(f"查詢失敗: {e}")
