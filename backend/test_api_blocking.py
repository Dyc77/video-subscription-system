"""
測試 API 阻塞問題

此腳本會：
1. 觸發背景掃描（長時間任務）
2. 立即測試其他 API 端點
3. 驗證 API 是否在掃描期間保持可用

使用方式：
    python test_api_blocking.py
"""
import requests
import time
import sys

# ========== 設定區 ==========
API_BASE_URL = "http://localhost:8000"
YOUR_TOKEN = "YOUR_JWT_TOKEN_HERE"  # 請替換成你的 JWT Token

# ============================


def test_api_blocking():
    """測試 API 是否被阻塞"""

    print("\n" + "=" * 70)
    print("🧪 API 阻塞測試工具")
    print("=" * 70)
    print(f"API 地址: {API_BASE_URL}")
    print(f"Token: {YOUR_TOKEN[:20]}..." if len(YOUR_TOKEN) > 20 else f"Token: {YOUR_TOKEN}")
    print("=" * 70 + "\n")

    headers = {
        "Authorization": f"Bearer {YOUR_TOKEN}",
        "Content-Type": "application/json"
    }

    # ========== 步驟 1: 觸發背景掃描 ==========
    print("📡 步驟 1: 觸發背景掃描...")
    print("-" * 70)

    try:
        start_time = time.time()
        response = requests.post(
            f"{API_BASE_URL}/api/channel/test/scan-background",
            headers=headers,
            timeout=10
        )
        elapsed_ms = (time.time() - start_time) * 1000

        if response.status_code == 200:
            data = response.json()
            print(f"✅ 背景掃描已啟動")
            print(f"⏱️  API 回應時間: {elapsed_ms:.2f} ms")
            print(f"🆔 進程 PID: {data.get('process_id')}")
            print(f"📝 進程名稱: {data.get('process_name')}")
            print()

            if elapsed_ms > 500:
                print("⚠️  警告：API 回應時間過長（> 500ms），可能仍有阻塞問題")
            else:
                print("✅ API 回應時間正常（< 500ms）")

        else:
            print(f"❌ 觸發失敗: HTTP {response.status_code}")
            print(f"錯誤訊息: {response.text}")
            return

    except requests.exceptions.Timeout:
        print("❌ 請求超時（> 10 秒），API 可能被阻塞了！")
        return
    except Exception as e:
        print(f"❌ 發生錯誤: {str(e)}")
        return

    print("\n" + "-" * 70)
    print("📡 步驟 2: 立即測試其他 API（驗證是否被阻塞）")
    print("-" * 70 + "\n")

    # ========== 步驟 2: 測試多個 API 端點 ==========
    test_endpoints = [
        ("GET", "/health", "健康檢查"),
        ("GET", "/api/video/list", "影片列表"),
        ("GET", "/api/channel/subscriptions/list", "訂閱列表"),
    ]

    results = []

    for method, endpoint, description in test_endpoints:
        print(f"🔍 測試: {description} ({endpoint})")

        try:
            start_time = time.time()

            if method == "GET":
                response = requests.get(
                    f"{API_BASE_URL}{endpoint}",
                    headers=headers,
                    timeout=5
                )
            elif method == "POST":
                response = requests.post(
                    f"{API_BASE_URL}{endpoint}",
                    headers=headers,
                    timeout=5
                )

            elapsed_ms = (time.time() - start_time) * 1000

            if response.status_code in [200, 201]:
                status = "✅ 成功"
                color = ""
            else:
                status = f"⚠️  HTTP {response.status_code}"
                color = ""

            print(f"   {status} - 回應時間: {elapsed_ms:.2f} ms")

            results.append({
                "endpoint": endpoint,
                "description": description,
                "success": response.status_code in [200, 201],
                "time_ms": elapsed_ms
            })

        except requests.exceptions.Timeout:
            print(f"   ❌ 超時（> 5 秒）- API 被阻塞了！")
            results.append({
                "endpoint": endpoint,
                "description": description,
                "success": False,
                "time_ms": 5000
            })

        except Exception as e:
            print(f"   ❌ 錯誤: {str(e)}")
            results.append({
                "endpoint": endpoint,
                "description": description,
                "success": False,
                "time_ms": 0
            })

        print()
        time.sleep(0.5)  # 稍微間隔一下

    # ========== 步驟 3: 總結 ==========
    print("=" * 70)
    print("📊 測試結果總結")
    print("=" * 70 + "\n")

    success_count = sum(1 for r in results if r["success"])
    total_count = len(results)
    avg_time = sum(r["time_ms"] for r in results) / total_count if total_count > 0 else 0

    print(f"成功率: {success_count}/{total_count} ({success_count/total_count*100:.1f}%)")
    print(f"平均回應時間: {avg_time:.2f} ms")
    print()

    if success_count == total_count and avg_time < 1000:
        print("🎉 測試通過！")
        print("✅ 所有 API 在掃描期間都能正常回應")
        print("✅ Multiprocessing 成功繞過 GIL，API 不被阻塞")
    elif success_count == total_count:
        print("⚠️  部分通過")
        print("✅ API 能回應，但速度較慢")
        print("💡 可能還有優化空間")
    else:
        print("❌ 測試失敗")
        print("❌ 某些 API 無法回應或超時")
        print("❌ 可能仍有阻塞問題")

    print("\n" + "=" * 70 + "\n")


if __name__ == "__main__":
    if YOUR_TOKEN == "YOUR_JWT_TOKEN_HERE":
        print("\n❌ 錯誤：請先設定你的 JWT Token")
        print("請編輯此檔案，將 YOUR_TOKEN 變數改為你的實際 Token\n")
        print("取得 Token 的方式：")
        print("1. 登入系統")
        print("2. 在瀏覽器開發者工具 → Application → Local Storage")
        print("3. 找到 'token' 或類似的 key\n")
        sys.exit(1)

    test_api_blocking()
