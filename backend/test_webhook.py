"""
測試 LINE Webhook
"""
import requests
import json
import hmac
import hashlib
import base64

# 從 .env 讀取
CHANNEL_SECRET = "61dee447282cc8bf903acd4a18a3bc2e"
WEBHOOK_URL = "http://localhost:8000/api/line/webhook"

# 模擬 LINE 發送的 Follow Event
follow_event = {
    "destination": "U1234567890",
    "events": [
        {
            "type": "follow",
            "timestamp": 1234567890,
            "source": {
                "type": "user",
                "userId": "Utest12345"
            },
            "replyToken": "test-reply-token",
            "mode": "active"
        }
    ]
}

# 轉換為 JSON 字串
body = json.dumps(follow_event)

# 計算 Signature
signature = base64.b64encode(
    hmac.new(
        CHANNEL_SECRET.encode('utf-8'),
        body.encode('utf-8'),
        hashlib.sha256
    ).digest()
).decode('utf-8')

# 發送請求
headers = {
    "Content-Type": "application/json",
    "X-Line-Signature": signature
}

print(f"發送測試請求到: {WEBHOOK_URL}")
print(f"X-Line-Signature: {signature}")
print(f"Body: {body}\n")

response = requests.post(WEBHOOK_URL, data=body, headers=headers)

print(f"狀態碼: {response.status_code}")
print(f"回應: {response.text}")

if response.status_code == 200:
    print("\n✅ Webhook 測試成功！")
else:
    print(f"\n❌ Webhook 測試失敗！")
