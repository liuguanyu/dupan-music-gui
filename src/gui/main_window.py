import wx
import wx.lib.agw.aui as aui
import wx.adv
import requests
from io import BytesIO
from PIL import Image, ImageDraw
from src.auth import AuthManager
from src.api import BaiduPanAPI
from src.player import AudioPlayer
from src.gui.login_window import LoginWindow
from src.gui.playlist_panel import PlaylistPanel
from src.gui.player_panel import PlayerPanel
from src.gui.file_browser import FileBrowser

# 定义ID
REFRESH_TOKEN_TIMER_ID = wx.NewId()
ID_PLAY = wx.NewId()
ID_PREVIOUS = wx.NewId()
ID_NEXT = wx.NewId()
ID_VOLUME_UP = wx.NewId()
ID_VOLUME_DOWN = wx.NewId()
ID_MUTE = wx.NewId()

class MainWindow(wx.Frame):
    def __init__(self):
        super().__init__(None, title="百度云音乐播放器", size=(800, 600))
        
        # 创建快捷键绑定
        self.setup_accelerators()
        
        # 创建系统托盘图标
        self.setup_tray_icon()
        
        # 设置窗口图标（使用系统默认图标）
        self.SetIcon(wx.Icon(wx.ArtProvider.GetBitmap(wx.ART_INFORMATION)))
        
        # 初始化认证管理器、API客户端和播放器
        self.auth = AuthManager()
        self.api_client = BaiduPanAPI(self.auth)
        self.player = AudioPlayer(self.api_client)
        
        # 检查登录状态
        if not self.auth.is_logged_in():
            self.Destroy()
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
        self.playlist_panel = PlaylistPanel(self, self.api_client)
        self.playlist_panel.set_player(self.player)
        self._mgr.AddPane(
            self.playlist_panel,
            aui.AuiPaneInfo().Name("playlist").Caption("播放列表")
                .Left().Layer(0).Position(0).CloseButton(False)
                .BestSize(200, -1).MinSize(150, -1)
        )
        
        # 创建中央内容面板
        self.content_panel = FileBrowser(self, self.api_client)
        self._mgr.AddPane(
            self.content_panel,
            aui.AuiPaneInfo().Name("content").Caption("文件浏览器")
                .CenterPane()
        )
        
        # 创建底部控制面板
        self.control_panel = PlayerPanel(self)
        self.control_panel.set_player(self.player)  # 使用set_player方法设置播放器实例
        self._mgr.AddPane(
            self.control_panel,
            aui.AuiPaneInfo().Name("controls").Caption("播放控制")
                .Bottom().Layer(0).Position(0).CloseButton(False)
                .BestSize(-1, 80).MinSize(-1, 60)
        )
        
        # 更新AUI管理器
        self._mgr.Update()
        
        # 绑定文件浏览器的添加到播放列表事件
        self.content_panel.Bind(wx.EVT_BUTTON, self.on_add_to_playlist)
        
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
        
    def on_add_to_playlist(self, event):
        """处理添加到播放列表事件"""
        if event.GetId() == wx.ID_ADD:
            files = event.GetClientData()
            if files:
                # 将文件添加到播放列表
                for file in files:
                    self.playlist_panel.add_file(file)
                
    def setup_accelerators(self):
        """设置键盘快捷键"""
        # 创建快捷键表
        accelerator_table = wx.AcceleratorTable([
            # 空格键：播放/暂停
            (wx.ACCEL_NORMAL, wx.WXK_SPACE, ID_PLAY),
            # Ctrl+左箭头：上一曲
            (wx.ACCEL_CTRL, wx.WXK_LEFT, ID_PREVIOUS),
            # Ctrl+右箭头：下一曲
            (wx.ACCEL_CTRL, wx.WXK_RIGHT, ID_NEXT),
            # 上箭头：增加音量
            (wx.ACCEL_NORMAL, wx.WXK_UP, ID_VOLUME_UP),
            # 下箭头：减小音量
            (wx.ACCEL_NORMAL, wx.WXK_DOWN, ID_VOLUME_DOWN),
            # Ctrl+M：静音
            (wx.ACCEL_CTRL, ord('M'), ID_MUTE)
        ])
        self.SetAcceleratorTable(accelerator_table)
        
        # 绑定快捷键事件
        self.Bind(wx.EVT_MENU, self.on_play_pause, id=ID_PLAY)
        self.Bind(wx.EVT_MENU, self.on_previous_track, id=ID_PREVIOUS)
        self.Bind(wx.EVT_MENU, self.on_next_track, id=ID_NEXT)
        self.Bind(wx.EVT_MENU, self.on_volume_up, id=ID_VOLUME_UP)
        self.Bind(wx.EVT_MENU, self.on_volume_down, id=ID_VOLUME_DOWN)
        self.Bind(wx.EVT_MENU, self.on_mute, id=ID_MUTE)
        
    def on_play_pause(self, event):
        """播放/暂停快捷键处理"""
        if self.player:
            self.control_panel.on_play_pause(event)
            
    def on_previous_track(self, event):
        """上一曲快捷键处理"""
        if self.player:
            self.control_panel.on_previous(event)
            
    def on_next_track(self, event):
        """下一曲快捷键处理"""
        if self.player:
            self.control_panel.on_next(event)
            
    def on_volume_up(self, event):
        """增加音量快捷键处理"""
        if self.player:
            current_volume = self.control_panel.volume_slider.GetValue()
            new_volume = min(100, current_volume + 5)
            self.control_panel.volume_slider.SetValue(new_volume)
            self.control_panel.on_volume_change(None)
            
    def on_volume_down(self, event):
        """减小音量快捷键处理"""
        if self.player:
            current_volume = self.control_panel.volume_slider.GetValue()
            new_volume = max(0, current_volume - 5)
            self.control_panel.volume_slider.SetValue(new_volume)
            self.control_panel.on_volume_change(None)
            
    def on_mute(self, event):
        """静音快捷键处理"""
        if self.player:
            self.control_panel.on_mute(event)
            
    def setup_tray_icon(self):
        """设置系统托盘图标"""
        self.tray_icon = wx.adv.TaskBarIcon()
        self.tray_icon.SetIcon(
            wx.ArtProvider.GetIcon(wx.ART_INFORMATION),
            "百度云音乐播放器"
        )
        
        # 绑定事件
        self.tray_icon.Bind(wx.adv.EVT_TASKBAR_LEFT_DOWN, self.on_tray_click)
        self.tray_icon.Bind(wx.adv.EVT_TASKBAR_RIGHT_DOWN, self.on_tray_right_click)
        
        # 绑定窗口图标化事件
        self.Bind(wx.EVT_ICONIZE, self.on_iconize)
        
    def create_tray_menu(self):
        """创建托盘菜单"""
        menu = wx.Menu()
        
        # 播放/暂停
        play_item = menu.Append(ID_PLAY, "播放/暂停")
        menu.Bind(wx.EVT_MENU, self.on_play_pause, play_item)
        
        # 上一曲
        prev_item = menu.Append(ID_PREVIOUS, "上一曲")
        menu.Bind(wx.EVT_MENU, self.on_previous_track, prev_item)
        
        # 下一曲
        next_item = menu.Append(ID_NEXT, "下一曲")
        menu.Bind(wx.EVT_MENU, self.on_next_track, next_item)
        
        menu.AppendSeparator()
        
        # 显示/隐藏主窗口
        show_item = menu.Append(wx.ID_ANY, "显示主窗口" if not self.IsShown() else "隐藏主窗口")
        menu.Bind(wx.EVT_MENU, self.on_show_hide, show_item)
        
        # 退出
        exit_item = menu.Append(wx.ID_EXIT, "退出")
        menu.Bind(wx.EVT_MENU, self.on_exit, exit_item)
        
        return menu
        
    def on_tray_click(self, event):
        """处理托盘图标左键点击"""
        self.on_show_hide(event)
        
    def on_tray_right_click(self, event):
        """处理托盘图标右键点击"""
        menu = self.create_tray_menu()
        self.tray_icon.PopupMenu(menu)
        menu.Destroy()
        
    def on_show_hide(self, event):
        """显示/隐藏主窗口"""
        if self.IsShown():
            self.Hide()
        else:
            self.Show()
            self.Raise()
            
    def on_iconize(self, event):
        """处理窗口最小化事件"""
        if event.IsIconized():
            self.Hide()
            
    def on_exit(self, event):
        """退出应用程序"""
        if wx.MessageBox("确定要退出应用程序吗？", "确认",
                        wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION) == wx.YES:
            self.tray_icon.Destroy()
            self.Close(True)
            
    def on_close(self, event):
        """关闭窗口事件处理"""
        self.refresh_timer.Stop()
        self._mgr.UnInit()
        del self._mgr
        self.tray_icon.Destroy()
        self.Destroy()

if __name__ == "__main__":
    app = wx.App()
    frame = MainWindow()
    frame.Show()
    app.MainLoop()
