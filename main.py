#!/usr/bin/env python3
"""
百度云音乐播放器主入口
"""

import wx
import sys
import logging
from src.gui.login_window import LoginWindow
from src.gui.main_window import MainWindow
from src.auth import AuthManager

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    try:
        app = wx.App()
        
        # 检查是否已登录
        auth = AuthManager()
        if auth.is_logged_in():
            frame = MainWindow()
        else:
            frame = LoginWindow()
            
        frame.Show()
        app.MainLoop()
    except Exception as e:
        logger.error(f"应用程序启动失败: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
