import wx
import numpy as np
from .visualizer_base import VisualizerBase

class SpectrumVisualizer(VisualizerBase):
    """频谱可视化器"""
    
    def __init__(self, parent, player):
        """初始化频谱可视化器
        
        Args:
            parent: 父窗口
            player: 播放器实例
        """
        super().__init__(parent, player)
        
        # 频谱特定配置
        self.config.update({
            'bar_width': 4,  # 频谱柱宽度
            'bar_spacing': 2,  # 频谱柱间距
            'smoothing': 0.8,  # 平滑系数
            'fft_size': 1024,  # FFT大小
            'min_db': -70,  # 最小分贝值
            'max_db': 0,  # 最大分贝值
        })
        
        # 初始化频谱数据
        self.fft_data = np.zeros(self.config['fft_size'] // 2)
        
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
        """绘制频谱
        
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
        
        # 计算可以显示的频谱柱数量
        bar_width = self.config['bar_width']
        bar_spacing = self.config['bar_spacing']
        num_bars = min(
            len(self.fft_data),
            int(width / (bar_width + bar_spacing))
        )
        
        # 重采样频谱数据以匹配显示的柱数
        display_data = np.interp(
            np.linspace(0, len(self.fft_data), num_bars),
            np.arange(len(self.fft_data)),
            self.fft_data
        )
        
        # 设置画笔和画刷
        color = wx.Colour(self.config['color'])
        gc.SetPen(wx.Pen(color))
        
        # 绘制频谱柱
        for i in range(num_bars):
            # 计算柱子位置和高度
            x = i * (bar_width + bar_spacing)
            bar_height = display_data[i] * height
            
            # 创建渐变画刷
            gradient = gc.CreateLinearGradientBrush(
                x, height,
                x, height - bar_height,
                color.ChangeLightness(120),  # 顶部颜色
                color.ChangeLightness(50)    # 底部颜色
            )
            gc.SetBrush(gradient)
            
            # 绘制频谱柱
            gc.DrawRectangle(x, height - bar_height, bar_width, bar_height)
            
            # 绘制柱顶小方块
            gc.SetBrush(wx.Brush(color.ChangeLightness(140)))
            gc.DrawRectangle(x, height - bar_height - 2, bar_width, 2)
