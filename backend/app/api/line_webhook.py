"""
LINE Webhook API
處理 LINE 平台發送的事件
"""
from fastapi import APIRouter, Request, HTTPException, Depends, Header
from sqlalchemy.orm import Session
from linebot.v3.webhook import WebhookParser
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent,
    FollowEvent,
    UnfollowEvent
)
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    TextMessage,
    ReplyMessageRequest,
    PushMessageRequest
)
from app.core.config import settings
from app.db.database import get_db
from app.models.models import User
from app.services.line_message_service import line_message_service
from app.utils.auth import verify_token, create_access_token
from app.models.line_binding_codes import binding_code_store
import logging
from datetime import timedelta
import urllib.parse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/line", tags=["line"])

# 初始化 LINE Webhook Parser
parser = WebhookParser(settings.LINE_CHANNEL_SECRET)


@router.post("/webhook")
async def line_webhook(
    request: Request,
    x_line_signature: str = Header(None),
    db: Session = Depends(get_db)
):
    """
    LINE Webhook 接收端點

    此端點接收來自 LINE 平台的各種事件：
    - FollowEvent: 使用者加入好友
    - UnfollowEvent: 使用者封鎖/刪除好友
    - MessageEvent: 使用者發送訊息
    """
    # 獲取請求 body
    body = await request.body()
    body_str = body.decode('utf-8')

    try:
        # 驗證 LINE Signature
        events = parser.parse(body_str, x_line_signature)
    except InvalidSignatureError:
        logger.error("LINE Webhook 簽名驗證失敗")
        raise HTTPException(status_code=400, detail="Invalid signature")

    # 處理每個事件
    for event in events:
        try:
            if isinstance(event, FollowEvent):
                # 使用者加入好友
                await handle_follow_event(event, db)

            elif isinstance(event, UnfollowEvent):
                # 使用者封鎖/刪除好友
                await handle_unfollow_event(event, db)

            elif isinstance(event, MessageEvent) and isinstance(event.message, TextMessageContent):
                # 使用者發送文字訊息
                await handle_text_message(event, db)

        except Exception as e:
            logger.error(f"處理 LINE 事件失敗: {str(e)}")
            continue

    return {"status": "ok"}


async def handle_follow_event(event: FollowEvent, db: Session):
    """
    處理使用者加入好友事件

    當使用者加入好友時，發送歡迎訊息並引導綁定
    """
    line_user_id = event.source.user_id

    logger.info(f"🆕 新使用者加入好友: {line_user_id}")

    try:
        # 檢查是否已經綁定
        logger.info("檢查使用者是否已綁定...")
        existing_user = db.query(User).filter(
            User.line_user_id == line_user_id
        ).first()

        configuration = Configuration(access_token=settings.LINE_CHANNEL_ACCESS_TOKEN)
        api_client = ApiClient(configuration)
        messaging_api = MessagingApi(api_client)

        if existing_user:
            logger.info(f"使用者已綁定: {existing_user.account}")
            # 已綁定，發送歡迎訊息
            message = TextMessage(
                text=f"🎉 歡迎回來！\n\n"
                     f"您的帳號 {existing_user.account} 已經綁定此 LINE 帳號。\n\n"
                     f"當您訂閱的頻道有新影片時，我們會立即通知您！"
            )

            request = ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[message]
            )

            logger.info("發送歡迎訊息（已綁定）...")
            messaging_api.reply_message(request)
            logger.info("✅ 歡迎訊息發送成功")

        else:
            logger.info("使用者未綁定，發送引導訊息...")
            # 未綁定，發送引導訊息
            message = TextMessage(
                text=f"👋 歡迎使用 VideoHub LINE 通知！\n\n"
                     f"📌 如何綁定帳號：\n"
                     f"1. 登入 VideoHub 網站\n"
                     f"2. 前往「設定」頁面\n"
                     f"3. 點擊「綁定 LINE」按鈕\n"
                     f"4. 複製專屬連結並開啟\n\n"
                     f"綁定後，您訂閱的頻道有新影片時，我們會立即通知您！"
            )

            request = ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[message]
            )

            logger.info("發送引導訊息...")
            messaging_api.reply_message(request)
            logger.info("✅ 引導訊息發送成功")

    except Exception as e:
        logger.error(f"❌ 處理加好友事件失敗: {str(e)}")
        logger.exception("詳細錯誤訊息：")


async def handle_unfollow_event(event: UnfollowEvent, db: Session):
    """
    處理使用者封鎖/刪除好友事件

    清除該使用者的 LINE 綁定資訊
    """
    line_user_id = event.source.user_id

    logger.info(f"使用者取消關注: {line_user_id}")

    # 清除綁定
    user = db.query(User).filter(
        User.line_user_id == line_user_id
    ).first()

    if user:
        user.line_user_id = None
        db.commit()
        logger.info(f"已清除使用者 {user.account} 的 LINE 綁定")


async def handle_text_message(event: MessageEvent, db: Session):
    """
    處理使用者發送的文字訊息

    提供簡單的互動回覆
    """
    line_user_id = event.source.user_id
    text = event.message.text.strip()

    logger.info(f"收到訊息 from {line_user_id}: {text}")

    configuration = Configuration(access_token=settings.LINE_CHANNEL_ACCESS_TOKEN)
    api_client = ApiClient(configuration)
    messaging_api = MessagingApi(api_client)

    # 檢查是否為 BIND-XXXXXX 格式的 Token
    if text.startswith("BIND-"):
        logger.info(f"收到綁定 Token: {text}")

        try:
            # 在資料庫中查找誰的 line_user_id 欄位存了這個 Token
            user = db.query(User).filter(User.line_user_id == text).first()

            if not user:
                logger.warning(f"Token 無效或已過期: {text}")
                message = TextMessage(
                    text="❌ 驗證碼無效或已過期\n\n"
                         "請回到網站重新取得綁定連結。\n"
                         "💡 驗證碼有效期限為 10 分鐘。"
                )
                request = ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[message]
                )
                messaging_api.reply_message(request)
                return

            logger.info(f"找到使用者: {user.account} (ID: {user.user_no})")

            # 檢查是否有其他帳號已經綁定這個 LINE User ID
            existing_binding = db.query(User).filter(
                User.line_user_id == line_user_id,
                User.user_no != user.user_no
            ).first()

            if existing_binding:
                logger.info(f"解除舊綁定: {existing_binding.account}")
                existing_binding.line_user_id = None

            # 🎯 關鍵步驟：將 Token 替換為真實的 LINE User ID
            logger.info(f"將 Token '{text}' 替換為真實 LINE ID: {line_user_id}")
            user.line_user_id = line_user_id
            db.commit()
            logger.info("✅ 資料庫更新成功")

            # 發送成功訊息
            logger.info("發送綁定成功訊息...")
            line_message_service.send_binding_success_message(
                line_user_id=line_user_id,
                user_name=user.account.split('@')[0]
            )

            logger.info(f"🎉 成功綁定使用者 {user.account} 到 LINE ID {line_user_id}")

        except Exception as e:
            logger.error(f"❌ 綁定失敗: {str(e)}")
            logger.exception("詳細錯誤訊息：")

            message = TextMessage(
                text="❌ 綁定失敗\n\n"
                     "請稍後再試或聯繫客服。"
            )
            request = ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[message]
            )
            messaging_api.reply_message(request)

    # 檢查是否為舊的 JWT Token 格式（保留向下兼容）
    elif text.startswith("BIND:") and len(text) > 10:
        # 綁定流程
        token = text.replace("BIND:", "").strip()

        logger.info(f"開始處理綁定請求，LINE User ID: {line_user_id}")
        logger.info(f"Token 前 20 字元: {token[:20]}...")

        try:
            # 驗證 JWT Token
            logger.info("驗證 JWT Token...")
            payload = verify_token(token)
            user_id = payload.get("user_id")
            logger.info(f"Token 驗證成功，User ID: {user_id}")

            # 查詢使用者
            logger.info(f"查詢使用者 {user_id}...")
            user = db.query(User).filter(User.user_no == user_id).first()

            if not user:
                logger.error(f"使用者 {user_id} 不存在")
                raise HTTPException(status_code=404, detail="使用者不存在")

            logger.info(f"找到使用者: {user.account}")

            # 檢查是否已綁定其他帳號
            logger.info("檢查現有綁定...")
            existing_binding = db.query(User).filter(
                User.line_user_id == line_user_id,
                User.user_no != user_id
            ).first()

            if existing_binding:
                logger.info(f"解除舊綁定: {existing_binding.account}")
                # 先解綁舊帳號
                existing_binding.line_user_id = None

            # 綁定新帳號
            logger.info(f"綁定 LINE ID {line_user_id} 到使用者 {user.account}")
            user.line_user_id = line_user_id
            db.commit()
            logger.info("資料庫更新成功")

            # 發送成功訊息
            logger.info("發送綁定成功訊息...")
            line_message_service.send_binding_success_message(
                line_user_id=line_user_id,
                user_name=user.account.split('@')[0]
            )

            logger.info(f"✅ 成功綁定使用者 {user.account} 到 LINE ID {line_user_id}")

        except Exception as e:
            logger.error(f"❌ 綁定失敗: {str(e)}")
            logger.exception("詳細錯誤訊息：")

            message = TextMessage(
                text=f"❌ 綁定失敗\n\n"
                     f"連結可能已過期或無效，請重新在網站上取得綁定連結。"
            )

            request = ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[message]
            )

            messaging_api.reply_message(request)

    else:
        # 一般訊息，回覆說明
        user = db.query(User).filter(User.line_user_id == line_user_id).first()

        if user:
            reply_text = (
                f"您好！您的帳號 {user.account} 已綁定成功。\n\n"
                f"💡 可用功能：\n"
                f"- 當訂閱頻道有新影片時自動通知\n\n"
                f"如需調整設定，請前往 VideoHub 網站的設定頁面。"
            )
        else:
            reply_text = (
                f"您好！請先在 VideoHub 網站完成帳號綁定。\n\n"
                f"📌 綁定步驟（只需 3 步）：\n"
                f"1️⃣ 登入 VideoHub 網站\n"
                f"2️⃣ 前往「設定」頁面\n"
                f"3️⃣ 點擊「綁定 LINE」→「開啟 LINE」\n\n"
                f"點擊按鈕後會自動回到這個聊天室，\n"
                f"傳送綁定訊息即可完成！"
            )

        message = TextMessage(text=reply_text)

        request = ReplyMessageRequest(
            reply_token=event.reply_token,
            messages=[message]
        )

        messaging_api.reply_message(request)


@router.post("/generate-binding-token")
async def generate_binding_token(
    db: Session = Depends(get_db),
    authorization: str = Header(None)
):
    """
    生成 LINE 綁定 Token 並暫存於 tb_user.line_user_id

    流程：
    1. 生成隨機 Token (BIND-XXXXXX)
    2. 暫存到該用戶的 line_user_id 欄位
    3. 返回 Deep Link URL

    Returns:
        {
            "token": "BIND-123456",
            "deep_link": "https://line.me/R/oaMessage/@333wpdzm/?text=BIND-123456",
            "expires_in": 600
        }
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未提供認證令牌")

    token = authorization.replace("Bearer ", "")

    try:
        # 驗證 JWT Token
        payload = verify_token(token)
        user_id = payload.get("user_id")

        # 查詢使用者
        user = db.query(User).filter(User.user_no == user_id).first()

        if not user:
            raise HTTPException(status_code=404, detail="使用者不存在")

        # 生成 Token (BIND-XXXXXX 格式，6 位隨機數字)
        import random
        random_code = ''.join(random.choices('0123456789', k=6))
        binding_token = f"BIND-{random_code}"

        # 暫存到 line_user_id 欄位
        user.line_user_id = binding_token
        db.commit()

        # 建立 Deep Link
        # 使用 oaMessage 格式，但 URL encode 處理要正確
        # 參考：https://developers.line.biz/en/docs/messaging-api/using-line-url-scheme/
        # 正確格式：https://line.me/R/oaMessage/@LINE_ID/?MESSAGE (不需要 text= 參數)
        line_bot_id = "@333wpdzm"
        # 重要：LINE oaMessage 不需要 URL encode，直接放純文字
        deep_link = f"https://line.me/R/oaMessage/{line_bot_id}/?{binding_token}"

        logger.info(f"為使用者 {user.account} 生成綁定 Token: {binding_token}")

        return {
            "token": binding_token,
            "deep_link": deep_link,
            "expires_in": 600,  # 10 分鐘（前端可顯示倒數計時）
            "instructions": [
                "點擊下方按鈕開啟 LINE",
                "LINE 會自動填入驗證碼",
                "按下傳送即可完成綁定"
            ]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"生成綁定 Token 失敗: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-binding-link")
async def generate_binding_link(
    db: Session = Depends(get_db),
    authorization: str = Header(None)
):
    """
    生成 LINE 綁定連結（舊方法，保留作為備用）

    前端呼叫此 API 取得專屬綁定連結

    Returns:
        {
            "binding_link": "line://ti/p/@your_bot_id?text=BIND:eyJ0eXAi...",
            "binding_token": "eyJ0eXAi...",
            "expires_in": 1800  # 30 分鐘
        }
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未提供認證令牌")

    token = authorization.replace("Bearer ", "")

    try:
        # 驗證 JWT Token
        payload = verify_token(token)
        user_id = payload.get("user_id")

        # 查詢使用者
        user = db.query(User).filter(User.user_no == user_id).first()

        if not user:
            raise HTTPException(status_code=404, detail="使用者不存在")

        # 生成新的短效 Token（30 分鐘有效）
        binding_token = create_access_token(
            data={"user_id": user_id, "purpose": "line_binding"},
            expires_delta=timedelta(minutes=30)
        )

        # 建立 LINE 綁定連結
        # 請替換 @your_bot_id 為您的實際 LINE Bot Basic ID
        line_bot_id = "@333wpdzm"  # TODO: 替換為您的 LINE Bot Basic ID
        binding_text = f"BIND:{binding_token}"

        # URL Encode
        encoded_text = urllib.parse.quote(binding_text)

        binding_link = f"https://line.me/R/ti/p/{line_bot_id}?text={encoded_text}"

        logger.info(f"為使用者 {user.account} 生成綁定連結")

        return {
            "binding_link": binding_link,
            "binding_token": binding_token,
            "expires_in": 1800,  # 30 分鐘
            "instructions": [
                "1. 點擊下方「開啟 LINE」按鈕",
                "2. 加入 VideoHub 官方帳號為好友（如果尚未加入）",
                "3. 系統會自動傳送綁定訊息",
                "4. 等待綁定成功通知"
            ]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"生成綁定連結失敗: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/unbind")
async def unbind_line(
    db: Session = Depends(get_db),
    authorization: str = Header(None)
):
    """
    解除 LINE 綁定
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未提供認證令牌")

    token = authorization.replace("Bearer ", "")

    try:
        # 驗證 JWT Token
        payload = verify_token(token)
        user_id = payload.get("user_id")

        # 查詢使用者
        user = db.query(User).filter(User.user_no == user_id).first()

        if not user:
            raise HTTPException(status_code=404, detail="使用者不存在")

        if not user.line_user_id:
            raise HTTPException(status_code=400, detail="尚未綁定 LINE")

        # 清除綁定
        user.line_user_id = None
        db.commit()

        logger.info(f"使用者 {user.account} 已解除 LINE 綁定")

        return {
            "status": "success",
            "message": "已成功解除 LINE 綁定"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"解除綁定失敗: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/binding-status")
async def get_binding_status(
    db: Session = Depends(get_db),
    authorization: str = Header(None)
):
    """
    查詢 LINE 綁定狀態
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未提供認證令牌")

    token = authorization.replace("Bearer ", "")

    try:
        # 驗證 JWT Token
        payload = verify_token(token)
        user_id = payload.get("user_id")

        # 查詢使用者
        user = db.query(User).filter(User.user_no == user_id).first()

        if not user:
            raise HTTPException(status_code=404, detail="使用者不存在")

        # 檢查是否已綁定：line_user_id 有值且不是 BIND- 開頭的暫存 Token
        is_bound = bool(user.line_user_id) and not (user.line_user_id or "").startswith("BIND-")

        return {
            "is_bound": is_bound,
            "line_user_id": user.line_user_id if is_bound else None
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查詢綁定狀態失敗: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
