import feedparser
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.models.models import YoutubeChannel, YoutubeVideo, NotificationLog, User, UserSubscription
from app.services.notification_service import notification_service
from app.services.gemini_service import gemini_service
from datetime import datetime
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)


class WatcherService:
    """RSS 監測爬蟲服務 - The Watcher"""

    def __init__(self, db: Session):
        self.db = db

    def scan_all_channels(self) -> int:
        """掃描所有啟用的頻道，並發送通知"""
        try:
            # 獲取所有啟用的頻道
            active_channels = self.db.query(YoutubeChannel).filter(
                YoutubeChannel.channel_status == 1
            ).all()

            logger.info(f"開始掃描 {len(active_channels)} 個頻道...")

            total_new_videos = 0

            for channel in active_channels:
                new_videos = self._scan_channel(channel)
                total_new_videos += new_videos

            logger.info(f"掃描完成！發現 {total_new_videos} 個新影片")

            print(f"掃描完成！發現 {total_new_videos} 個新影片")

            # 【新邏輯】不管有沒有新影片，都檢查是否該發送通知
            # 因為可能有其他使用者訂閱了已存在的頻道
            self._send_notifications_from_view()

            return total_new_videos

        except Exception as e:
            logger.error(f"掃描頻道時發生錯誤: {str(e)}")
            raise

    def _scan_channel(self, channel: YoutubeChannel) -> int:
        """
        掃描單一頻道的RSS feed

        Args:
            channel: YouTube頻道物件

        Returns:
            int: 新發現的影片數量
        """
        try:
            # 1. 建立RSS URL
            rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel.channel_id}"

            # 2. 抓取RSS feed
            feed = feedparser.parse(rss_url)

            if not feed.entries:
                logger.warning(f"頻道 {channel.title} 沒有RSS內容")
                return 0

            new_videos_count = 0

            # 3. 【VIP 檢查】判斷這個頻道是否有高級會員訂閱
            has_vip = self._check_if_channel_has_vip(channel.channel_no)
            if has_vip:
                logger.info(f"💎 頻道 {channel.title} 有高級會員訂閱，將自動生成摘要")

            # 4. 遍歷影片條目（只抓最新 3 個，不要太多）
            for entry in feed.entries[:3]:
                video_id = entry.yt_videoid

                # 檢查影片是否已存在
                existing_video = self.db.query(YoutubeVideo).filter(
                    YoutubeVideo.video_id == video_id
                ).first()

                if existing_video:
                    continue  # 影片已存在，跳過

                # 5. 新影片：写入数据库
                new_video = YoutubeVideo(
                    channel_no=channel.channel_no,
                    video_id=video_id,
                    title=entry.title,
                    video_url=entry.link,
                    thumbnail_url=self._extract_thumbnail(entry),
                    published_at=self._parse_published_time(entry),
                    summary_status=0  # 預設尚未生成摘要
                )

                self.db.add(new_video)
                self.db.flush()  # 立即取得 video_no，但不提交事務
                new_videos_count += 1

                logger.info(f"新影片: {entry.title} ({video_id})")

                # 6. 【VIP 優先通道】如果有高級會員，立即生成摘要
                if has_vip:
                    self._auto_generate_summary_for_vip(new_video)

            # 7. 更新頻道的最後檢查時間
            channel.last_check_time = datetime.utcnow()
            self.db.commit()

            if new_videos_count > 0:
                logger.info(f"頻道 {channel.title} 發現 {new_videos_count} 部新影片")

            return new_videos_count

        except Exception as e:
            logger.error(f"掃描頻道 {channel.title} 失敗: {str(e)}")
            self.db.rollback()
            return 0

    def _extract_thumbnail(self, entry) -> str:
        """從RSS entry中提取縮圖URL"""
        try:
            # 嘗試從 media_thumbnail 中獲取
            if hasattr(entry, 'media_thumbnail'):
                return entry.media_thumbnail[0]['url']

            # 備用方案：使用YouTube預設格式
            video_id = entry.yt_videoid
            return f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"

        except Exception as e:
            logger.error(f"提取縮圖失敗: {str(e)}")
            # 返回佔位圖
            return "https://via.placeholder.com/480x360?text=No+Thumbnail"

    def _parse_published_time(self, entry) -> datetime:
        """解析影片發布時間"""
        try:
            # 嘗試從 published_parsed 獲取
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                import time
                return datetime.fromtimestamp(time.mktime(entry.published_parsed))

            # 備用方案：使用當前時間
            return datetime.utcnow()

        except Exception as e:
            logger.error(f"解析發布時間失敗: {str(e)}")
            return datetime.utcnow()

    def _check_if_channel_has_vip(self, channel_no: int) -> bool:
        """
        檢查這個頻道是否有任何高級會員 (membership_level = 1) 訂閱

        Args:
            channel_no: 頻道編號

        Returns:
            bool: True 表示有高級會員訂閱
        """
        try:
            # 查詢訂閱這個頻道的高級會員數量
            vip_count = self.db.query(User).join(
                UserSubscription,
                User.user_no == UserSubscription.user_no
            ).filter(
                UserSubscription.channel_no == channel_no,
                User.membership_level == 1  # 高級會員
            ).count()

            return vip_count > 0

        except Exception as e:
            logger.error(f"檢查 VIP 訂閱失敗: {str(e)}")
            return False

    def _auto_generate_summary_for_vip(self, video: YoutubeVideo):
        """
        【VIP 優先通道】為高級會員自動生成摘要

        Args:
            video: 影片物件（必須已經有 video_no）

        注意：
        - 只為「24 小時內發布的新影片」自動生成摘要
        - 這是為了防止使用者升級 VIP 時，系統回填大量舊影片摘要（浪費 API Quota）
        - 策略：「過去被動，未來主動」（Passive Past, Active Future）
        """
        try:
            # 【安全閥】檢查影片發布時間 - 只為 24 小時內的新片生成摘要
            from datetime import timedelta
            is_fresh_video = video.published_at > (datetime.utcnow() - timedelta(hours=24))

            if not is_fresh_video:
                logger.info(f"⏭️ 跳過舊影片自動摘要: {video.title} (發布於 {video.published_at})")
                return  # 舊影片保持 summary_status = 0，使用者可手動點選生成

            logger.info(f"💎 開始為 VIP 生成摘要: {video.title} (發布於 {video.published_at})")

            # 標記為處理中
            video.summary_status = 1
            self.db.commit()

            # 呼叫 Gemini Service 生成摘要
            summary_text = gemini_service.generate_summary_from_url(
                youtube_url=video.video_url,
                video_id=video.video_id
            )

            if summary_text:
                # 更新摘要內容和狀態
                video.summary_content = summary_text
                video.summary_status = 2  # 完成
                self.db.commit()

                logger.info(f"✅ VIP 自動摘要完成: {video.title}")
            else:
                # 生成失敗
                video.summary_status = 3
                self.db.commit()
                logger.warning(f"⚠️ VIP 自動摘要失敗（可能無字幕）: {video.title}")

        except Exception as e:
            logger.error(f"❌ VIP 自動摘要發生錯誤: {str(e)}")
            # 將狀態設為失敗，但不影響主流程
            try:
                video.summary_status = 3
                self.db.commit()
            except:
                pass

    def _send_notifications_from_view(self):
        """
        【新架構】從 vw_PendingNotifications View 撈出待發送清單
        並根據會員等級發送不同內容的通知
        加入通知間隔時間檢查
        """

        print("開始發送通知...")

        try:
            # 1. 查詢待發送通知清單
            # View 已經處理了所有過濾邏輯：
            # - 頻道通知開關 (is_notification_enabled = 1)
            # - 防重複發送 (nl.log_id IS NULL)
            # - 通知間隔時間檢查
            query = text("""
                SELECT
                    user_no, account, email, membership_level,
                    video_no, video_id, video_title, video_url, thumbnail_url,
                    summary_status, summary_content,
                    channel_no, channel_title
                FROM vw_PendingNotifications
                ORDER BY user_no, channel_title, published_at DESC
            """)

            result = self.db.execute(query)
            pending_notifications = result.fetchall()

            if not pending_notifications:
                logger.info("沒有待發送的通知")
                return

            logger.info(f"找到 {len(pending_notifications)} 筆待發送通知")

            # 2. 按用戶分組（同一用戶的多部影片合併成一封 Email）
            notifications_by_user = {}
            for row in pending_notifications:
                user_no = row.user_no
                if user_no not in notifications_by_user:
                    notifications_by_user[user_no] = {
                        'email': row.email or row.account,  # 優先使用 email，沒有則用 account
                        'account': row.account,
                        'membership_level': row.membership_level,
                        'videos': []
                    }

                # 根據會員等級決定是否附帶摘要
                video_info = {
                    'channel_title': row.channel_title,
                    'video_title': row.video_title,
                    'video_url': row.video_url,
                    'thumbnail_url': row.thumbnail_url,
                }

                # 【關鍵邏輯】高級會員 (membership_level=1) 且摘要已生成 -> 附帶完整摘要
                if row.membership_level == 1 and row.summary_status == 2 and row.summary_content:
                    video_info['summary'] = row.summary_content  # 完整摘要
                else:
                    video_info['summary'] = None

                notifications_by_user[user_no]['videos'].append({
                    'info': video_info,
                    'video_no': row.video_no,
                    'channel_no': row.channel_no,
                })

            # 3. 逐一發送通知
            for user_no, user_data in notifications_by_user.items():
                try:
                    # 準備影片清單（轉換格式給 notification_service）
                    videos_for_email = [v['info'] for v in user_data['videos']]

                    # 【新增】查詢使用者資訊（需要 line_user_id 和 enable_line）
                    from app.models.models import UserSetting
                    user = self.db.query(User).filter(User.user_no == user_no).first()
                    user_setting = self.db.query(UserSetting).filter(
                        UserSetting.user_no == user_no
                    ).first()

                    # 發送 Email（如果啟用）
                    if user_setting and user_setting.enable_email == 1:
                        print(f"發送 Email 通知給 {user_data['email']} ({len(user_data['videos'])} 部影片)")
                        email_success = notification_service.send_new_videos_notification(
                            to_email=user_data['email'],
                            user_name=user_data['account'].split('@')[0],
                            new_videos=videos_for_email,
                            membership_level=user_data['membership_level']
                        )

                        if email_success:
                            # 記錄 Email 通知
                            for video_data in user_data['videos']:
                                log = NotificationLog(
                                    user_no=user_no,
                                    video_no=video_data['video_no'],
                                    channel_no=video_data['channel_no'],
                                    send_method='email',
                                    is_success=1
                                )
                                self.db.add(log)

                    # 【新增】發送 LINE 通知（如果啟用且已綁定）
                    if user_setting and user_setting.enable_line == 1 and user.line_user_id:
                        print(f"發送 LINE 通知給 {user.line_user_id} ({len(user_data['videos'])} 部影片)")

                        from app.services.line_message_service import line_message_service

                        line_success = line_message_service.send_new_videos_notification(
                            line_user_id=user.line_user_id,
                            user_name=user_data['account'].split('@')[0],
                            new_videos=videos_for_email,
                            membership_level=user_data['membership_level']
                        )

                        if line_success:
                            # 記錄 LINE 通知
                            for video_data in user_data['videos']:
                                log = NotificationLog(
                                    user_no=user_no,
                                    video_no=video_data['video_no'],
                                    channel_no=video_data['channel_no'],
                                    send_method='line',
                                    is_success=1
                                )
                                self.db.add(log)

                    self.db.commit()
                    logger.info(f"成功發送通知給使用者 {user_no}")

                except Exception as e:
                    logger.error(f"發送通知給用戶 {user_no} 時發生錯誤: {str(e)}")
                    self.db.rollback()
                    continue

        except Exception as e:
            logger.error(f"從 View 發送通知時發生錯誤: {str(e)}")
            self.db.rollback()
