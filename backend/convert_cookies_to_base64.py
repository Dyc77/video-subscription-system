#!/usr/bin/env python3
"""
將 cookies.txt 轉換為 Base64 編碼

使用方法：
    python convert_cookies_to_base64.py

這個腳本會讀取 cookies.txt 並輸出 Base64 編碼的字串，
你可以將這個字串設定為 Zeabur 的環境變數 YOUTUBE_COOKIES_BASE64
"""

import base64
import os
import sys


def convert_cookies_to_base64(cookies_file_path='cookies.txt'):
    """
    將 cookies.txt 轉換為 Base64 編碼

    Args:
        cookies_file_path: cookies.txt 的路徑

    Returns:
        str: Base64 編碼的字串
    """
    # 檢查檔案是否存在
    if not os.path.exists(cookies_file_path):
        print(f"❌ 錯誤：找不到檔案 {cookies_file_path}")
        print(f"📁 當前目錄：{os.getcwd()}")
        print("\n請確保 cookies.txt 存在於當前目錄中")
        sys.exit(1)

    # 讀取檔案內容
    try:
        with open(cookies_file_path, 'r', encoding='utf-8') as f:
            cookies_content = f.read()
    except Exception as e:
        print(f"❌ 讀取檔案失敗：{e}")
        sys.exit(1)

    # 轉換為 Base64
    cookies_bytes = cookies_content.encode('utf-8')
    base64_encoded = base64.b64encode(cookies_bytes).decode('utf-8')

    return base64_encoded, len(cookies_content)


def main():
    print("=" * 60)
    print("🍪 YouTube Cookies Base64 轉換工具")
    print("=" * 60)
    print()

    # 轉換 cookies
    base64_string, original_size = convert_cookies_to_base64('cookies.txt')

    # 輸出結果
    print("✅ 轉換成功！")
    print(f"📊 原始檔案大小：{original_size} bytes")
    print(f"📊 Base64 長度：{len(base64_string)} 字元")
    print()
    print("=" * 60)
    print("📋 Base64 編碼結果（複製以下內容）：")
    print("=" * 60)
    print()
    print(base64_string)
    print()
    print("=" * 60)
    print("📝 使用說明：")
    print("=" * 60)
    print()
    print("1. 複製上面的 Base64 字串")
    print("2. 前往 Zeabur Dashboard")
    print("3. 找到你的專案 -> Environment Variables")
    print("4. 新增環境變數：")
    print("   Key: YOUTUBE_COOKIES_BASE64")
    print("   Value: (貼上複製的 Base64 字串)")
    print("5. 儲存並重新部署")
    print()
    print("✨ 完成後，你的應用程式就能從環境變數讀取 cookies 了！")
    print()

    # 儲存到檔案（選擇性）
    output_file = 'cookies_base64.txt'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(base64_string)
    print(f"💾 Base64 字串已儲存至 {output_file}")
    print()


if __name__ == '__main__':
    main()
