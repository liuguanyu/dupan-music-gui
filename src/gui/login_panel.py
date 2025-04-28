"""百度云音乐播放器登录面板"""

import wx
import webbrowser
from src.auth import AuthManager

CHECK_LOGIN_TIMER_ID = wx.NewId()
class LoginPanel(wx.Panel):
    def __init__(self, parent):
        super().__init__(parent)
        self.SetBackgroundColour(wx.BLACK)
        self.auth = AuthManager()
        self.init_ui()
        
        # 创建定时器
        self.check_timer = wx.Timer(self, CHECK_LOGIN_TIMER_ID)
        self.Bind(wx.EVT_TIMER, self.check_login_status, self.check_timer)
        
        # 自动显示二维码
        wx.CallAfter(self.show_qr_code)
        
    def init_ui(self):
        """初始化登录界面"""
        vbox = wx.BoxSizer(wx.VERTICAL)
        
        # 标题
        title = wx.StaticText(self, label="百度云音乐播放器登录")
        title.SetFont(wx.Font(16, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        title.SetForegroundColour(wx.WHITE)
        vbox.Add(title, 0, wx.ALIGN_CENTER|wx.TOP|wx.BOTTOM, 20)
        
        # 二维码显示区域
        qr_panel = wx.Panel(self, size=(320, 320))
        qr_panel.SetBackgroundColour(wx.BLACK)
        
        self.qr_bitmap = wx.StaticBitmap(qr_panel, size=(300, 300))
        qr_sizer = wx.BoxSizer(wx.VERTICAL)
        qr_sizer.Add(self.qr_bitmap, 0, wx.ALIGN_CENTER|wx.ALL, 10)
        qr_panel.SetSizer(qr_sizer)
        
        vbox.Add(qr_panel, 0, wx.ALIGN_CENTER|wx.ALL, 20)
        
        # 状态提示
        self.status_label = wx.StaticText(self, label="正在加载二维码...")
        self.status_label.SetForegroundColour(wx.WHITE)
        vbox.Add(self.status_label, 0, wx.ALIGN_CENTER|wx.BOTTOM, 10)
        
        # 提示文本
        hint_text = wx.StaticText(self, label="请使用百度网盘APP扫描二维码登录")
        hint_text.SetForegroundColour(wx.WHITE)
        vbox.Add(hint_text, 0, wx.ALIGN_CENTER|wx.BOTTOM, 10)
        
        # 按钮区域
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        self.refresh_btn = wx.Button(self, label="刷新二维码")
        self.refresh_btn.Bind(wx.EVT_BUTTON, self.on_refresh)
        btn_sizer.Add(self.refresh_btn, 0, wx.RIGHT, 10)
        
        self.cancel_btn = wx.Button(self, label="取消")
        self.cancel_btn.Bind(wx.EVT_BUTTON, self.on_cancel)
        btn_sizer.Add(self.cancel_btn, 0)
        
        vbox.Add(btn_sizer, 0, wx.ALIGN_CENTER|wx.ALL, 10)
        
        # 设置主布局并使其适应窗口大小
        self.SetSizer(vbox)
        self.Layout()
        
        # 确保按钮可点击
        self.refresh_btn.Enable(True)
        self.cancel_btn.Enable(True)
        
        
    def show_qr_code(self):
        """显示二维码"""
        try:
            self.auth.show_login_qr(self)
            self.status_label.SetLabel("请使用百度云APP扫描二维码")
            self.Layout()
            
            # 启动定时器，每1秒检查一次登录状态
            self.check_timer.Start(1000)
        except Exception as e:
            self.status_label.SetLabel(f"生成二维码失败: {str(e)}")
            self.Layout()
        
    def on_cancel(self, event):
        """处理取消按钮点击事件"""
        self.check_timer.Stop()
        self.GetParent().Close()
        
    def update_status(self, message):
        """更新状态信息"""
        self.status_label.SetLabel(message)
        self.Layout()
        
    def check_login_status(self, event):
        """检查登录状态"""
        try:
            # 强制检查授权状态
            status = self.auth.check_auth_status()
            
            if status:
                self.check_timer.Stop()
                # 保存token并立即显示主窗口
                self.auth._save_token()
                wx.CallAfter(self._show_main_window)
            else:
                # 检查授权状态
                if hasattr(self.auth, 'device_code') and self.auth.device_code:
                    # 根据轮询间隔更新定时器
                    if self.check_timer.GetInterval() != self.auth.poll_interval * 1000:
                        self.check_timer.Stop()
                        self.check_timer.Start(self.auth.poll_interval * 1000)
                    self.update_status("等待扫码授权...")
                else:
                    self.update_status("二维码已过期，请点击刷新")
                    self.check_timer.Stop()
        except ValueError as e:
            self.update_status(str(e))
            self.check_timer.Stop()
        except Exception as e:
            self.update_status(f"登录出错: {str(e)}")
            self.check_timer.Stop()
            
    def on_refresh(self, event):
        """刷新二维码"""
        self.show_qr_code()
        
    def _show_main_window(self):
        """显示主窗口"""
        try:
            # 关闭登录窗口，显示主窗口
            self.GetParent().Close()
            from src.gui.main_window import MainWindow
            main_window = MainWindow()
            main_window.Show()
        except Exception as e:
            wx.MessageBox(f"打开主窗口失败: {str(e)}", "错误", wx.OK | wx.ICON_ERROR)
