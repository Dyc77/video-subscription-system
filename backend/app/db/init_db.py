"""
資料庫初始化腳本

執行此腳本以建立所有資料庫表
"""
from app.db.database import Base, engine
from app.models.models import User, YoutubeChannel, YoutubeVideo, UserSubscription
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def init_database():
    """
    建立所有資料庫表
    """
    try:
        logger.info("開始建立資料庫表...")

        # 建立所有表
        Base.metadata.create_all(bind=engine)

        logger.info("資料庫表建立完成！")
        logger.info("建立的表:")
        logger.info("- tb_User")
        logger.info("- tb_YoutubeChannel")
        logger.info("- tb_YoutubeVideo")
        logger.info("- tb_UserSubscription")

    except Exception as e:
        logger.error(f"建立資料庫表失敗: {str(e)}")
        raise


def drop_all_tables():
    """
    刪除所有資料庫表 (謹慎使用!)
    """
    try:
        logger.warning("警告: 即將刪除所有資料庫表!")
        confirmation = input("確認刪除? (yes/no): ")

        if confirmation.lower() == "yes":
            Base.metadata.drop_all(bind=engine)
            logger.info("所有資料庫表已刪除")
        else:
            logger.info("操作已取消")

    except Exception as e:
        logger.error(f"刪除資料庫表失敗: {str(e)}")
        raise


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--drop":
        drop_all_tables()
    else:
        init_database()
