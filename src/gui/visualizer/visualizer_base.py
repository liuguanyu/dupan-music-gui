import wx
import numpy as np
from abc import abstractmethod

class VisualizerBase(wx.Panel):
    """可视化器基类"""
    
    def __init__(self, parent, player):
        """初始化可视化器
        
        Args:
            parent: 父窗口
            player: 播放器实例，用于获取音频数据
        """
        super().__init__(parent)
        
        # 保存播放器引用
        self.player = player
        
        # 设置默认配置
        self.config = {
            'fps': 30,  # 刷新率
            'color': '#00ff00',  # 默认颜色
            'background': '#000000',  # 背景色
            'sensitivity': 1.0,  # 灵敏度
        }
        
        # 创建定时器用于刷新显示
        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.on_timer)
        
        # 绑定绘制事件
        self.Bind(wx.EVT_PAINT, self.on_paint)
        self.Bind(wx.EVT_SIZE, self.on_size)
        
        # 双缓冲绘制
        self.SetDoubleBuffered(True)
        
        # 启动定时器
        self.timer.Start(1000 // self.config['fps'])
        
    def get_audio_data(self):
        """从播放器获取音频数据
        
        Returns:
            numpy.ndarray: 音频数据数组
        """
        if not self.player or not self.player.is_playing():
            return np.zeros(1024)
            
        try:
            # 获取原始音频数据
            data = self.player.get_audio_data()
            if data is None:
                return np.zeros(1024)
                
            # 应用灵敏度
            data = data * self.config['sensitivity']
            
            return data
            
        except Exception as e:
            print(f"获取音频数据失败: {e}")
            return np.zeros(1024)
            
    def set_config(self, **kwargs):
        """更新配置
        
        Args:
            **kwargs: 配置参数，可包含fps、color、background、sensitivity等
        """
        self.config.update(kwargs)
        
        # 更新定时器
        if 'fps' in kwargs:
            self.timer.Stop()
            self.timer.Start(1000 // self.config['fps'])
            
        # 重绘
        self.Refresh()
        
    def start(self):
        """启动可视化"""
        if not self.timer.IsRunning():
            self.timer.Start(1000 // self.config['fps'])
            
    def stop(self):
        """停止可视化"""
        if self.timer.IsRunning():
            self.timer.Stop()
            
    def on_timer(self, event):
        """定时器事件处理"""
        self.Refresh()
        
    def on_size(self, event):
        """大小变更事件处理"""
        self.Refresh()
        event.Skip()
        
    def on_paint(self, event):
        """绘制事件处理"""
        dc = wx.BufferedPaintDC(self)
        gc = wx.GraphicsContext.Create(dc)
        
        if not gc:
            return
            
        # 获取窗口大小
        width, height = self.GetSize()
        
        # 清空背景
        gc.SetBrush(wx.Brush(self.config['background']))
        gc.DrawRectangle(0, 0, width, height)
        
        # 调用具体实现的绘制方法
        self.draw(gc, width, height)
        
    @abstractmethod
    def draw(self, gc, width, height):
        """绘制可视化效果
        
        Args:
            gc: 图形上下文
            width: 绘制区域宽度
            height: 绘制区域高度
        """
        pass
