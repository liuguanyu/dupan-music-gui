import wx
from src.player import AudioPlayer, PlayMode
from .visualizer.waveform_visualizer import WaveformVisualizer
from .visualizer.spectrum_visualizer import SpectrumVisualizer
from .visualizer.circular_visualizer import CircularVisualizer

class PlayerPanel(wx.Panel):
    def __init__(self, parent):
        super().__init__(parent)
        
        # 播放器实例（由MainWindow设置）
        self.player = None
        
        # 当前可视化器
        self.current_visualizer = None
        self.visualizer_types = {
            "波形": WaveformVisualizer,
            "频谱": SpectrumVisualizer,
            "环形": CircularVisualizer
        }
        
        # 创建界面
        self._init_ui()
        
        # 绑定事件
        self._bind_events()
        
        # 初始化定时器用于更新进度条
        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.on_timer)
        self.timer.Start(1000)  # 每秒更新一次
        
    def _init_ui(self):
        """初始化界面"""
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # 创建可视化器面板
        visualizer_panel = wx.Panel(self)
        visualizer_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        # 可视化器选择器
        self.visualizer_choice = wx.Choice(visualizer_panel, choices=list(self.visualizer_types.keys()))
        self.visualizer_choice.SetSelection(0)
        visualizer_sizer.Add(self.visualizer_choice, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        
        # 可视化器容器
        self.visualizer_container = wx.Panel(visualizer_panel)
        self.visualizer_container.SetBackgroundColour(wx.BLACK)
        visualizer_sizer.Add(self.visualizer_container, 1, wx.EXPAND | wx.ALL, 5)
        
        visualizer_panel.SetSizer(visualizer_sizer)
        main_sizer.Add(visualizer_panel, 1, wx.EXPAND)
        
        # 创建播放信息面板
        info_panel = wx.Panel(self)
        info_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        # 歌曲信息
        song_info = wx.BoxSizer(wx.VERTICAL)
        self.song_name = wx.StaticText(info_panel, label="未播放")
        self.artist_name = wx.StaticText(info_panel, label="")
        song_info.Add(self.song_name, 0, wx.BOTTOM, 5)
        song_info.Add(self.artist_name, 0)
        info_sizer.Add(song_info, 1, wx.ALL | wx.EXPAND, 5)
        
        info_panel.SetSizer(info_sizer)
        main_sizer.Add(info_panel, 0, wx.EXPAND)
        
        # 创建控制面板
        control_panel = wx.Panel(self)
        control_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        # 播放模式按钮
        self.mode_btn = wx.Button(control_panel, label="列表循环")
        control_sizer.Add(self.mode_btn, 0, wx.ALL, 5)
        
        # 上一曲按钮
        self.prev_btn = wx.Button(control_panel, label="上一曲")
        control_sizer.Add(self.prev_btn, 0, wx.ALL, 5)
        
        # 播放/暂停按钮
        self.play_btn = wx.Button(control_panel, label="播放")
        control_sizer.Add(self.play_btn, 0, wx.ALL, 5)
        
        # 下一曲按钮
        self.next_btn = wx.Button(control_panel, label="下一曲")
        control_sizer.Add(self.next_btn, 0, wx.ALL, 5)
        
        # 音量控制
        self.volume_slider = wx.Slider(control_panel, value=100, minValue=0, 
                                     maxValue=100, style=wx.SL_HORIZONTAL)
        control_sizer.Add(self.volume_slider, 1, wx.ALL | wx.EXPAND, 5)
        
        control_panel.SetSizer(control_sizer)
        main_sizer.Add(control_panel, 0, wx.EXPAND)
        
        # 创建进度条面板
        progress_panel = wx.Panel(self)
        progress_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        # 当前时间
        self.time_current = wx.StaticText(progress_panel, label="00:00")
        progress_sizer.Add(self.time_current, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        
        # 进度条
        self.progress_slider = wx.Slider(progress_panel, value=0, minValue=0, 
                                       maxValue=100, style=wx.SL_HORIZONTAL)
        progress_sizer.Add(self.progress_slider, 1, wx.ALL | wx.EXPAND, 5)
        
        # 总时长
        self.time_total = wx.StaticText(progress_panel, label="00:00")
        progress_sizer.Add(self.time_total, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        
        progress_panel.SetSizer(progress_sizer)
        main_sizer.Add(progress_panel, 0, wx.EXPAND)
        
        self.SetSizer(main_sizer)
        
    def _bind_events(self):
        """绑定事件处理"""
        # 播放控制事件
        self.play_btn.Bind(wx.EVT_BUTTON, self.on_play_pause)
        self.mode_btn.Bind(wx.EVT_BUTTON, self.on_change_mode)
        self.prev_btn.Bind(wx.EVT_BUTTON, self.on_prev_track)
        self.next_btn.Bind(wx.EVT_BUTTON, self.on_next_track)
        
        # 可视化器选择事件
        self.visualizer_choice.Bind(wx.EVT_CHOICE, self.on_visualizer_change)
        
        # 进度条事件
        self.progress_slider.Bind(wx.EVT_SLIDER, self.on_seek)
        
        # 音量控制事件
        self.volume_slider.Bind(wx.EVT_SLIDER, self.on_volume_change)
        
    def on_timer(self, event):
        """定时器事件处理，用于更新进度条"""
        if self.player and self.player.is_playing():
            current_time = self.player.get_position()
            total_time = self.player.get_length()
            
            if total_time > 0:
                # 更新进度条
                progress = (current_time / total_time) * 100
                self.progress_slider.SetValue(int(progress))
                
                # 更新时间显示
                self.time_current.SetLabel(self._format_time(current_time))
                self.time_total.SetLabel(self._format_time(total_time))
                
    def on_play_pause(self, event):
        """播放/暂停按钮事件处理"""
        if self.player:
            if self.player.is_playing():
                self.player.pause()
                self.play_btn.SetLabel("播放")
            else:
                self.player.play()
                self.play_btn.SetLabel("暂停")
            
    def on_change_mode(self, event):
        """切换播放模式"""
        if self.player:
            current_mode = self.mode_btn.GetLabel()
            if current_mode == "列表循环":
                self.mode_btn.SetLabel("单曲循环")
                self.player.set_play_mode(PlayMode.SINGLE)  # 单曲循环
            elif current_mode == "单曲循环":
                self.mode_btn.SetLabel("随机播放")
                self.player.set_play_mode(PlayMode.RANDOM)  # 随机播放
            else:
                self.mode_btn.SetLabel("列表循环")
                self.player.set_play_mode(PlayMode.SEQUENCE)  # 列表循环
            
    def on_prev_track(self, event):
        """上一曲按钮事件处理"""
        if self.player:
            self.player.previous_track()
            
    def on_next_track(self, event):
        """下一曲按钮事件处理"""
        if self.player:
            self.player.next_track()
            
    def on_seek(self, event):
        """进度条拖动事件处理"""
        if self.player and self.player.get_length() > 0:
            position = (self.progress_slider.GetValue() / 100.0) * self.player.get_length()
            self.player.seek(position)
            
    def on_volume_change(self, event):
        """音量滑块事件处理"""
        if self.player:
            volume = self.volume_slider.GetValue() / 100.0
            self.player.set_volume(volume)
        
    def _format_time(self, seconds):
        """格式化时间显示"""
        minutes = int(seconds // 60)
        seconds = int(seconds % 60)
        return f"{minutes:02d}:{seconds:02d}"
        
    def update_track_info(self, track):
        """更新当前播放曲目信息"""
        if track:
            self.song_name.SetLabel(track['name'])
            self.artist_name.SetLabel(track.get('artist', '未知艺术家'))
        else:
            self.song_name.SetLabel("未播放")
            self.artist_name.SetLabel("")
            
    def set_player(self, player):
        """设置播放器实例"""
        self.player = player
        
        # 初始化默认可视化器
        if self.player:
            self.init_visualizer()
            
    def init_visualizer(self):
        """初始化可视化器"""
        if self.current_visualizer:
            self.current_visualizer.stop()
            self.current_visualizer.Destroy()
            
        visualizer_type = self.visualizer_types[self.visualizer_choice.GetString(
            self.visualizer_choice.GetSelection()
        )]
        self.current_visualizer = visualizer_type(self.visualizer_container, self.player)
        
        # 调整可视化器大小
        container_size = self.visualizer_container.GetSize()
        self.current_visualizer.SetSize(container_size)
        
        # 启动可视化
        self.current_visualizer.start()
        
    def on_visualizer_change(self, event):
        """可视化器切换事件处理"""
        if self.player:
            self.init_visualizer()
