import wx
import numpy as np
from .visualizer_base import VisualizerBase

class WaveformVisualizer(VisualizerBase):
    """波形可视化器"""
    
    def __init__(self, parent, player):
        """初始化波形可视化器
        
        Args:
            parent: 父窗口
            player: 播放器实例
        """
        super().__init__(parent, player)
        
        # 波形特定配置
        self.config.update({
            'line_width': 2,  # 线条宽度
            'interpolation': True,  # 是否使用插值平滑
            'mirror': True,  # 是否镜像显示
        })
        
        # 历史数据缓存，用于平滑过渡
        self.history = np.zeros(1024)
        
    def draw(self, gc, width, height):
        """绘制波形
        
        Args:
            gc: 图形上下文
            width: 绘制区域宽度
            height: 绘制区域高度
        """
        # 获取音频数据
        data = self.get_audio_data()
        
        # 平滑过渡
        alpha = 0.3  # 平滑系数
        self.history = alpha * data + (1 - alpha) * self.history
        
        # 准备绘制
        gc.SetPen(wx.Pen(self.config['color'], self.config['line_width']))
        
        # 计算缩放比例
        scale_y = height / 4  # 留出上下边距
        samples = len(self.history)
        scale_x = width / (samples - 1)
        
        # 创建路径
        path = gc.CreatePath()
        
        # 绘制上半部分波形
        y_center = height / 2
        path.MoveToPoint(0, y_center - self.history[0] * scale_y)
        
        for i in range(1, samples):
            x = i * scale_x
            y = y_center - self.history[i] * scale_y
            
            if self.config['interpolation'] and i > 1:
                # 使用贝塞尔曲线进行平滑
                x_prev = (i - 1) * scale_x
                y_prev = y_center - self.history[i - 1] * scale_y
                cx = (x + x_prev) / 2
                path.AddQuadCurveToPoint(cx, y_prev, x, y)
            else:
                path.AddLineToPoint(x, y)
                
        # 如果启用镜像显示，绘制下半部分
        if self.config['mirror']:
            # 从右到左绘制镜像波形
            for i in range(samples - 1, -1, -1):
                x = i * scale_x
                y = y_center + self.history[i] * scale_y
                
                if self.config['interpolation'] and i < samples - 1:
                    x_next = (i + 1) * scale_x
                    y_next = y_center + self.history[i + 1] * scale_y
                    cx = (x + x_next) / 2
                    path.AddQuadCurveToPoint(cx, y_next, x, y)
                else:
                    path.AddLineToPoint(x, y)
                    
        # 闭合路径
        path.CloseSubpath()
        
        # 填充波形
        gc.SetBrush(wx.Brush(wx.Colour(self.config['color']).ChangeLightness(80)))
        gc.DrawPath(path)
