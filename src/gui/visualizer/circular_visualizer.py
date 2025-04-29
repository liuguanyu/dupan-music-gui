import wx
import numpy as np
from math import pi, sin, cos
from .visualizer_base import VisualizerBase

class CircularVisualizer(VisualizerBase):
    """环形频谱可视化器"""
    
    def __init__(self, parent, player):
        """初始化环形频谱可视化器
        
        Args:
            parent: 父窗口
            player: 播放器实例
        """
        super().__init__(parent, player)
        
        # 环形频谱特定配置
        self.config.update({
            'inner_radius': 50,  # 内圆半径
            'bar_width': 5,  # 频谱柱宽度（角度）
            'rotation_speed': 0.5,  # 旋转速度
            'smoothing': 0.8,  # 平滑系数
            'fft_size': 1024,  # FFT大小
            'min_db': -70,  # 最小分贝值
            'max_db': 0,  # 最大分贝值
        })
        
        # 初始化频谱数据和旋转角度
        self.fft_data = np.zeros(self.config['fft_size'] // 2)
        self.rotation = 0.0
        
    def process_audio_data(self, data):
        """处理音频数据，计算频谱
        
        Args:
            data: 原始音频数据
            
        Returns:
            numpy.ndarray: 处理后的频谱数据
        """
        # 应用汉宁窗
        windowed_data = data * np.hanning(len(data))
        
        # 执行FFT
        fft = np.fft.fft(windowed_data)[:len(data)//2]
        
        # 计算频谱幅度（分贝）
        magnitude = np.abs(fft)
        magnitude = 20 * np.log10(magnitude)
        
        # 归一化到配置的分贝范围
        magnitude = np.clip(magnitude, self.config['min_db'], self.config['max_db'])
        magnitude = (magnitude - self.config['min_db']) / (self.config['max_db'] - self.config['min_db'])
        
        return magnitude
        
    def draw(self, gc, width, height):
        """绘制环形频谱
        
        Args:
            gc: 图形上下文
            width: 绘制区域宽度
            height: 绘制区域高度
        """
        # 获取并处理音频数据
        raw_data = self.get_audio_data()
        current_fft = self.process_audio_data(raw_data)
        
        # 平滑处理
        self.fft_data = self.config['smoothing'] * self.fft_data + \
                       (1 - self.config['smoothing']) * current_fft
        
        # 更新旋转角度
        self.rotation += self.config['rotation_speed']
        if self.rotation >= 360:
            self.rotation = 0
            
        # 计算中心点和最大半径
        center_x = width / 2
        center_y = height / 2
        max_radius = min(width, height) / 2 - 10
        
        # 设置画笔
        color = wx.Colour(self.config['color'])
        gc.SetPen(wx.Pen(color))
        
        # 计算可显示的频谱柱数量
        num_bars = int(360 / self.config['bar_width'])
        
        # 重采样频谱数据以匹配显示的柱数
        display_data = np.interp(
            np.linspace(0, len(self.fft_data), num_bars),
            np.arange(len(self.fft_data)),
            self.fft_data
        )
        
        # 绘制环形频谱
        for i in range(num_bars):
            # 计算角度
            angle = (i * self.config['bar_width'] + self.rotation) * pi / 180
            
            # 计算频谱柱高度
            bar_height = display_data[i] * (max_radius - self.config['inner_radius'])
            
            # 计算起点和终点
            start_x = center_x + self.config['inner_radius'] * cos(angle)
            start_y = center_y + self.config['inner_radius'] * sin(angle)
            end_x = center_x + (self.config['inner_radius'] + bar_height) * cos(angle)
            end_y = center_y + (self.config['inner_radius'] + bar_height) * sin(angle)
            
            # 创建渐变画刷
            gradient = gc.CreateLinearGradientBrush(
                start_x, start_y,
                end_x, end_y,
                color.ChangeLightness(120),  # 内侧颜色
                color.ChangeLightness(50)    # 外侧颜色
            )
            gc.SetBrush(gradient)
            
            # 计算频谱柱的四个角点
            half_width = self.config['bar_width'] * pi / 360
            points = []
            
            # 内圆上的两个点
            angle1 = angle - half_width
            angle2 = angle + half_width
            points.append((
                center_x + self.config['inner_radius'] * cos(angle1),
                center_y + self.config['inner_radius'] * sin(angle1)
            ))
            points.append((
                center_x + self.config['inner_radius'] * cos(angle2),
                center_y + self.config['inner_radius'] * sin(angle2)
            ))
            
            # 外圆上的两个点
            outer_radius = self.config['inner_radius'] + bar_height
            points.append((
                center_x + outer_radius * cos(angle2),
                center_y + outer_radius * sin(angle2)
            ))
            points.append((
                center_x + outer_radius * cos(angle1),
                center_y + outer_radius * sin(angle1)
            ))
            
            # 绘制频谱柱
            path = gc.CreatePath()
            path.MoveToPoint(points[0][0], points[0][1])
            for x, y in points[1:]:
                path.AddLineToPoint(x, y)
            path.CloseSubpath()
            gc.DrawPath(path)
            
        # 绘制内圆
        gc.SetBrush(wx.Brush(color.ChangeLightness(140)))
        gc.DrawEllipse(
            center_x - self.config['inner_radius'],
            center_y - self.config['inner_radius'],
            self.config['inner_radius'] * 2,
            self.config['inner_radius'] * 2
        )
