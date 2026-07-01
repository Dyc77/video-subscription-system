from sqlalchemy.orm import Session
from app.models.models import YoutubeVideo, User
from app.services.youtube_service import youtube_service
from app.services.gemini_service import gemini_service
import logging
import time

logger = logging.getLogger(__name__)


class SummaryService:
    """摘要生成服务 - The Brain"""

    def __init__(self, db: Session):
        self.db = db

    def generate_summary(self, video_id: str, user_id: int) -> dict:
        """
        生成影片摘要 (On-Demand 模式)

        Args:
            video_id: YouTube 影片 ID
            user_id: 用户 ID

        Returns:
            dict: 包含摘要状态和内容的字典
        """
        try:
            # 1. 权限检查
            user = self.db.query(User).filter(User.user_no == user_id).first()
            if not user:
                return {
                    "status": "error",
                    "message": "用户不存在",
                    "summary_status": 0
                }

            if user.membership_level == 0:
                return {
                    "status": "error",
                    "message": "免费用户无法使用摘要功能，请升级为 Premium 会员",
                    "summary_status": 0
                }

            # 2. 查询影片
            video = self.db.query(YoutubeVideo).filter(
                YoutubeVideo.video_id == video_id
            ).first()

            if not video:
                return {
                    "status": "error",
                    "message": "影片不存在",
                    "summary_status": 0
                }

            # 3. 状态检查 (Race Condition Handling)
            if video.summary_status == 2:
                # CASE 2: 已有缓存，直接返回
                logger.info(f"影片 {video_id} 摘要已存在，直接返回缓存")
                return {
                    "status": "success",
                    "message": "摘要已生成",
                    "summary_status": 2,
                    "summary_content": video.summary_content,
                    "video_id": video_id
                }

            elif video.summary_status == 3:
                # CASE: 之前处理失败（无字幕）
                logger.info(f"影片 {video_id} 之前处理失败，返回错误信息")
                return {
                    "status": "error",
                    "message": "此影片无法生成摘要（无字幕或字幕获取失败）",
                    "summary_status": 3,
                    "video_id": video_id
                }

            elif video.summary_status == 1:
                # CASE 3: 正在处理中，等待并重试
                logger.info(f"影片 {video_id} 正在处理中，等待重试...")
                return {
                    "status": "processing",
                    "message": "AI 正在努力分析中，请稍候...",
                    "summary_status": 1,
                    "video_id": video_id,
                    "estimated_wait_seconds": 30  # 预估30秒
                }

            else:
                # CASE 1: 全新请求，开始生成
                logger.info(f"影片 {video_id} 开始生成摘要...")
                return self._generate_new_summary(video)

        except Exception as e:
            logger.error(f"生成摘要时发生错误: {str(e)}")
            return {
                "status": "error",
                "message": f"生成摘要失败: {str(e)}",
                "summary_status": 0
            }

    def _generate_new_summary(self, video: YoutubeVideo) -> dict:
        """
        生成新的摘要

        Args:
            video: 影片对象

        Returns:
            dict: 摘要结果
        """
        try:
            # 1. 更新状态为"处理中"（锁定）
            video.summary_status = 1
            self.db.commit()

            # 2. 获取字幕
            logger.info(f"正在获取影片 {video.video_id} 的字幕...")
            try:
                transcript = youtube_service.get_transcript(video.video_id)
                # 保存原始字幕
                video.transcript_text = transcript
            except Exception as transcript_error:
                # 字幕获取失败，标记为状态3
                video.summary_status = 3
                video.summary_content = None
                self.db.commit()
                logger.error(f"获取字幕失败: {str(transcript_error)}")
                return {
                    "status": "error",
                    "message": f"无法获取字幕: {str(transcript_error)}",
                    "summary_status": 3,
                    "video_id": video.video_id
                }

            # 3. 调用 Gemini 生成摘要
            logger.info(f"正在调用 Gemini API 生成摘要...")
            summary_content = gemini_service.generate_summary(transcript)

            # 4. 更新数据库
            video.summary_content = summary_content
            video.summary_status = 2
            self.db.commit()

            logger.info(f"影片 {video.video_id} 摘要生成完成")

            return {
                "status": "success",
                "message": "摘要生成完成",
                "summary_status": 2,
                "summary_content": summary_content,
                "video_id": video.video_id,
                "estimated_wait_seconds": 0  # 已完成，无需等待
            }

        except Exception as e:
            # 出错时标记为失败状态
            video.summary_status = 3
            self.db.commit()

            logger.error(f"生成摘要失败: {str(e)}")
            return {
                "status": "error",
                "message": f"生成摘要失败: {str(e)}",
                "summary_status": 3,
                "video_id": video.video_id
            }

    def _wait_and_retry(self, video_id: str, max_retries: int = 3) -> dict:
        """
        等待并重试获取摘要

        Args:
            video_id: 影片 ID
            max_retries: 最大重试次数

        Returns:
            dict: 摘要结果
        """
        for i in range(max_retries):
            time.sleep(2)  # 等待2秒

            # 重新查询状态
            video = self.db.query(YoutubeVideo).filter(
                YoutubeVideo.video_id == video_id
            ).first()

            if video.summary_status == 2:
                # 处理完成
                return {
                    "status": "success",
                    "message": "摘要生成完成",
                    "summary_status": 2,
                    "summary_content": video.summary_content,
                    "video_id": video_id
                }

        # 超时仍未完成
        return {
            "status": "processing",
            "message": "AI 正在努力分析中，请稍候...",
            "summary_status": 1,
            "video_id": video_id
        }
