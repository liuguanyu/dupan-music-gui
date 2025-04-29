import os
import vlc
import time
import threading
import numpy as np
from typing import Optional, Callable, List, Dict
from enum import Enum
import wx
from mutagen import File as MutagenFile

class PlayMode(Enum):
    """播放模式枚举"""
    SEQUENCE = 0  # 顺序播放
    RANDOM = 1    # 随机播放
    SINGLE = 2    # 单曲循环

class PlayState(Enum):
    """播放状态枚举"""
    STOPPED = 0   # 停止
    PLAYING = 1   # 播放中
    PAUSED = 2    # 暂停

class AudioPlayer:
    def __init__(self, api_client):
        """初始化音频播放器
        
        Args:
            api_client: 百度网盘API客户端实例
        """
        self.api_client = api_client
        
        # 初始化VLC实例和播放器
        self.instance = vlc.Instance()
        self.player = self.instance.media_player_new()
        self.media = None
        
        # 播放控制相关属性
        self.current_file = None
        self.play_mode = PlayMode.SEQUENCE
        self.state = PlayState.STOPPED
        self.volume = 100
        self._position = 0
        
        # 播放列表相关
        self.playlist = []
        self.current_index = -1
        
        # 回调函数
        self.on_state_changed: Optional[Callable[[PlayState], None]] = None
        self.on_position_changed: Optional[Callable[[float], None]] = None
        self.on_track_changed: Optional[Callable[[Dict], None]] = None
        self.on_error: Optional[Callable[[str], None]] = None
        
        # 音频分析相关
        self.audio_data = np.array([])
        self.spectrum_data = np.array([])
        
        # 启动更新线程
        self.update_thread = threading.Thread(target=self._update_loop, daemon=True)
        self.update_thread.start()
        
    def load_file(self, file_info: Dict) -> bool:
        """加载音频文件
        
        Args:
            file_info: 文件信息字典
            
        Returns:
            是否加载成功
        """
        try:
            # 获取文件下载链接
            download_url = self.api_client.get_file_download_url(file_info['fs_id'])
            
            # 创建媒体对象
            self.media = self.instance.media_new(download_url)
            self.player.set_media(self.media)
            
            # 更新当前文件信息
            self.current_file = file_info
            
            # 触发轨道改变事件
            if self.on_track_changed:
                self.on_track_changed(file_info)
                
            return True
            
        except Exception as e:
            if self.on_error:
                self.on_error(f"加载文件失败: {str(e)}")
            return False
            
    def play(self) -> None:
        """开始播放"""
        if self.state == PlayState.STOPPED and self.current_file:
            self.player.play()
            self.state = PlayState.PLAYING
            if self.on_state_changed:
                self.on_state_changed(self.state)
        elif self.state == PlayState.PAUSED:
            self.player.set_pause(0)
            self.state = PlayState.PLAYING
            if self.on_state_changed:
                self.on_state_changed(self.state)
                
    def pause(self) -> None:
        """暂停播放"""
        if self.state == PlayState.PLAYING:
            self.player.set_pause(1)
            self.state = PlayState.PAUSED
            if self.on_state_changed:
                self.on_state_changed(self.state)
                
    def stop(self) -> None:
        """停止播放"""
        self.player.stop()
        self.state = PlayState.STOPPED
        if self.on_state_changed:
            self.on_state_changed(self.state)
            
    def set_position(self, position: float) -> None:
        """设置播放位置
        
        Args:
            position: 播放位置(0-1)
        """
        if 0 <= position <= 1:
            self.player.set_position(position)
            self._position = position
            if self.on_position_changed:
                self.on_position_changed(position)
                
    def set_volume(self, volume: int) -> None:
        """设置音量
        
        Args:
            volume: 音量值(0-100)
        """
        if 0 <= volume <= 100:
            self.player.audio_set_volume(volume)
            self.volume = volume
            
    def get_position(self) -> float:
        """获取当前播放位置
        
        Returns:
            当前播放位置(0-1)
        """
        return self.player.get_position()
        
    def get_length(self) -> int:
        """获取当前音频长度（毫秒）
        
        Returns:
            音频长度
        """
        return self.player.get_length()
        
    def set_play_mode(self, mode: PlayMode) -> None:
        """设置播放模式
        
        Args:
            mode: 播放模式
        """
        self.play_mode = mode
        
    def next_track(self) -> bool:
        """播放下一曲
        
        Returns:
            是否成功切换到下一曲
        """
        if not self.playlist:
            return False
            
        if self.play_mode == PlayMode.RANDOM:
            # 随机模式：随机选择一个不同的索引
            if len(self.playlist) > 1:
                while True:
                    next_index = np.random.randint(0, len(self.playlist))
                    if next_index != self.current_index:
                        break
            else:
                next_index = 0
        else:
            # 顺序模式：移动到下一个索引
            next_index = (self.current_index + 1) % len(self.playlist)
            
        return self._play_index(next_index)
        
    def previous_track(self) -> bool:
        """播放上一曲
        
        Returns:
            是否成功切换到上一曲
        """
        if not self.playlist:
            return False
            
        if self.play_mode == PlayMode.RANDOM:
            # 随机模式：随机选择一个不同的索引
            if len(self.playlist) > 1:
                while True:
                    prev_index = np.random.randint(0, len(self.playlist))
                    if prev_index != self.current_index:
                        break
            else:
                prev_index = 0
        else:
            # 顺序模式：移动到上一个索引
            prev_index = (self.current_index - 1) % len(self.playlist)
            
        return self._play_index(prev_index)
        
    def set_playlist(self, playlist: List[Dict], start_index: int = 0) -> bool:
        """设置播放列表
        
        Args:
            playlist: 播放列表
            start_index: 开始播放的索引
            
        Returns:
            是否成功设置
        """
        if not playlist:
            return False
            
        self.stop()
        self.playlist = playlist
        return self._play_index(start_index)
        
    def _play_index(self, index: int) -> bool:
        """播放指定索引的音频
        
        Args:
            index: 播放索引
            
        Returns:
            是否成功播放
        """
        if 0 <= index < len(self.playlist):
            self.current_index = index
            if self.load_file(self.playlist[index]):
                self.play()
                return True
        return False
        
    def _update_loop(self) -> None:
        """更新循环，用于更新播放状态和触发回调"""
        while True:
            if self.state == PlayState.PLAYING:
                # 更新播放位置
                position = self.get_position()
                if position != self._position:
                    self._position = position
                    if self.on_position_changed:
                        wx.CallAfter(self.on_position_changed, position)
                        
                # 检查是否播放完成
                if position >= 0.99:
                    if self.play_mode == PlayMode.SINGLE:
                        # 单曲循环：重新播放当前曲目
                        wx.CallAfter(self._play_index, self.current_index)
                    else:
                        # 其他模式：播放下一曲
                        wx.CallAfter(self.next_track)
                        
            time.sleep(0.1)  # 降低CPU使用率
            
    def get_metadata(self) -> Dict:
        """获取当前音频的元数据
        
        Returns:
            元数据字典
        """
        if not self.current_file:
            return {}
            
        try:
            # 使用mutagen读取元数据
            audio = MutagenFile(self.current_file['path'])
            if audio:
                return {
                    'title': audio.get('title', [self.current_file['server_filename']])[0],
                    'artist': audio.get('artist', ['未知艺术家'])[0],
                    'album': audio.get('album', ['未知专辑'])[0],
                    'duration': audio.info.length
                }
        except:
            pass
            
        # 如果无法读取元数据，返回基本信息
        return {
            'title': self.current_file['server_filename'],
            'artist': '未知艺术家',
            'album': '未知专辑',
            'duration': 0
        }
        
    def get_audio_data(self) -> np.ndarray:
        """获取当前音频数据用于可视化
        
        Returns:
            音频数据数组
        """
        # TODO: 实现音频数据获取
        return self.audio_data
        
    def get_spectrum_data(self) -> np.ndarray:
        """获取频谱数据用于可视化
        
        Returns:
            频谱数据数组
        """
        # TODO: 实现频谱数据获取
        return self.spectrum_data
        
    def is_playing(self) -> bool:
        """检查是否正在播放
        
        Returns:
            是否正在播放
        """
        return self.state == PlayState.PLAYING
