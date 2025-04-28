import wx
import wx.lib.agw.aui as aui
import requests
from io import BytesIO
from PIL import Image, ImageDraw
from src.auth import AuthManager
from src.gui.login_window import LoginWindow

# 定义刷新token的定时器ID
REFRESH_TOKEN_TIMER_ID = wx.NewId()

class MainWindow(wx.Frame):
    def __init__(self):
        super().__init__(None, title="百度云音乐播放器", size=(800, 600))
        
        # 设置窗口图标（使用系统默认图标）
        self.SetIcon(wx.Icon(wx.ArtProvider.GetBitmap(wx.ART_INFORMATION)))
        
        # 初始化认证管理器
        self.auth = AuthManager()
        
        # 检查登录状态
        if not self.auth.is_logged_in():
            self.Show(False)
            login_window = LoginWindow()
            login_window.Show()
            return
            
        # 获取用户信息
        try:
            self.user_info = self.auth.get_user_info()
        except Exception as e:
            wx.MessageBox(f"获取用户信息失败: {str(e)}", "错误", wx.OK | wx.ICON_ERROR)
            self.user_info = None
        
        # 创建AUI管理器
        self._mgr = aui.AuiManager()
        self._mgr.SetManagedWindow(self)
        
        # 创建主面板
        self._setup_ui()
        
        # 创建定时器用于刷新token
        self.refresh_timer = wx.Timer(self, REFRESH_TOKEN_TIMER_ID)
        self.Bind(wx.EVT_TIMER, self.check_token, self.refresh_timer)
        # 每5分钟检查一次token状态
        self.refresh_timer.Start(5 * 60 * 1000)
        
        # 绑定事件
        self.Bind(wx.EVT_CLOSE, self.on_close)
        
    def _setup_ui(self):
        """初始化UI界面"""
        # 创建顶部用户信息面板
        self.user_panel = wx.Panel(self)
        user_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        # 添加弹性空间，使后面的内容靠右
        user_sizer.AddStretchSpacer()
        
        # 用户信息显示
        if self.user_info:
            # 添加用户头像
            if self.user_info['avatarUrl']:
                try:
                    # 下载头像
                    response = requests.get(self.user_info['avatarUrl'])
                    img_data = BytesIO(response.content)
                    pil_image = Image.open(img_data)
                    
                    # 调整大小为30x30
                    pil_image = pil_image.resize((30, 30), Image.Resampling.LANCZOS)
                    
                    # 创建圆形蒙版
                    mask = Image.new('L', (30, 30), 0)
                    draw = ImageDraw.Draw(mask)
                    draw.ellipse((0, 0, 30, 30), fill=255)
                    
                    # 应用圆形蒙版
                    output = Image.new('RGBA', (30, 30), (0, 0, 0, 0))
                    output.paste(pil_image, (0, 0))
                    output.putalpha(mask)
                    
                    # 转换为wx.Bitmap
                    wx_image = wx.Bitmap.FromBufferRGBA(
                        30, 30,
                        output.convert('RGBA').tobytes()
                    )
                    
                    # 创建静态位图并显示
                    avatar = wx.StaticBitmap(self.user_panel, -1, wx_image)
                    user_sizer.Add(avatar, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
                except Exception as e:
                    print(f"加载头像失败: {e}")
            
            # 用户名显示
            username_text = wx.StaticText(self.user_panel, label=self.user_info['username'])
            user_sizer.Add(username_text, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
            
            # VIP状态显示
            if self.user_info['isVip']:
                vip_text = wx.StaticText(self.user_panel, label="VIP用户")
                vip_text.SetForegroundColour(wx.Colour(255, 215, 0))  # 金色
                user_sizer.Add(vip_text, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        
        # 登出按钮
        logout_btn = wx.Button(self.user_panel, label="退出登录")
        logout_btn.Bind(wx.EVT_BUTTON, self.on_logout)
        user_sizer.Add(logout_btn, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        
        self.user_panel.SetSizer(user_sizer)
        
        # 创建透明的顶部面板
        pane_info = aui.AuiPaneInfo().Name("user").Caption("")\
            .Top().Layer(0).Position(0).CloseButton(False)\
            .BestSize(-1, 40).MinSize(-1, 40)\
            .CaptionVisible(False)\
            .PaneBorder(False)
            
        self._mgr.AddPane(self.user_panel, pane_info)
        
        # 创建左侧播放列表面板
        self.playlist_panel = wx.Panel(self)
        self._mgr.AddPane(
            self.playlist_panel,
            aui.AuiPaneInfo().Name("playlist").Caption("播放列表")
                .Left().Layer(0).Position(0).CloseButton(False)
                .BestSize(200, -1).MinSize(150, -1)
        )
        
        # 创建中央内容面板
        self.content_panel = wx.Panel(self)
        self._mgr.AddPane(
            self.content_panel,
            aui.AuiPaneInfo().Name("content").Caption("内容区域")
                .CenterPane()
        )
        
        # 创建底部控制面板
        self.control_panel = wx.Panel(self)
        self._mgr.AddPane(
            self.control_panel,
            aui.AuiPaneInfo().Name("controls").Caption("播放控制")
                .Bottom().Layer(0).Position(0).CloseButton(False)
                .BestSize(-1, 80).MinSize(-1, 60)
        )
        
        # 更新AUI管理器
        self._mgr.Update()
        
    def check_token(self, event):
        """检查token状态并在需要时刷新"""
        if not self.auth.is_logged_in():
            if not self.auth.refresh_token():
                self.handle_logout()
                return
                
    def on_logout(self, event):
        """处理登出事件"""
        if wx.MessageBox("确定要退出登录吗？", "确认", 
                        wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION) == wx.YES:
            self.handle_logout()
            
    def handle_logout(self):
        """处理登出逻辑"""
        self.auth.clear_token()
        self.refresh_timer.Stop()
        self.Hide()
        login_window = LoginWindow()
        login_window.Show()
        self.Close()
        
    def on_close(self, event):
        """关闭窗口事件处理"""
        self.refresh_timer.Stop()
        self._mgr.UnInit()
        del self._mgr
        self.Destroy()

if __name__ == "__main__":
    app = wx.App()
    frame = MainWindow()
    frame.Show()
    app.MainLoop()
