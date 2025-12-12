from ui.app import TrackingApp
from PyQt5.QtWidgets import QApplication
import sys
from utils.logger import setup_logger
import os
from dotenv import load_dotenv

load_dotenv()  # 加载 .env 文件

logger = setup_logger("MainApp")

if __name__ == "__main__":
    logger.info("🚀 启动无人机跟踪系统...")
    try:
        app = QApplication(sys.argv)
        window = TrackingApp()
        window.show()
        sys.exit(app.exec_())
        pass
    except Exception as e:
        logger.exception("程序发生未处理异常")