"""百度云音乐播放器登录窗口"""

import wx
from src.gui.login_panel import LoginPanel

class LoginWindow(wx.Frame):
    def __init__(self):
        super().__init__(
            None, 
            title="登录 - 百度云音乐播放器", 
            size=(400, 500),
            style=wx.DEFAULT_FRAME_STYLE & ~(wx.RESIZE_BORDER | wx.MAXIMIZE_BOX)
        )
        
        # 设置窗口图标
        self.SetIcon(wx.Icon(wx.ArtProvider.GetBitmap(wx.ART_TIP)))
        
        # 设置窗口背景颜色
        self.SetBackgroundColour(wx.BLACK)
        
        # 创建登录面板
        self.login_panel = LoginPanel(self)
        
        # 创建主布局
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        main_sizer.Add(self.login_panel, 1, wx.EXPAND)
        self.SetSizer(main_sizer)
        
        # 窗口居中显示
        self.Center()
        
        # 绑定关闭事件
        self.Bind(wx.EVT_CLOSE, self.on_close)
        
    def on_close(self, event):
        """处理窗口关闭事件"""
        self.login_panel.check_timer.Stop()
        event.Skip()
