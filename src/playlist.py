import os
import json
import time
from typing import List, Dict, Optional
from collections import deque
import threading

class PlaylistManager:
    def __init__(self, api_client):
        """初始化播放列表管理器
        
        Args:
            api_client: 百度网盘API客户端实例
        """
        self.api_client = api_client
        self.data_dir = os.path.join(os.path.expanduser("~"), ".dupan", "playlists")
        os.makedirs(self.data_dir, exist_ok=True)
        
        # 播放列表数据
        self.playlists: Dict[str, List[Dict]] = {}
        self.recent_played = deque(maxlen=30)  # 最近播放列表，最大30首
        
        # URL有效性检查
        self.url_cache: Dict[str, Dict] = {}
        self.url_check_interval = 3600  # URL有效性检查间隔（秒）
        
        # 加载保存的播放列表
        self._load_playlists()
        
        # 启动URL检查线程
        self.url_check_thread = threading.Thread(target=self._url_check_loop, daemon=True)
        self.url_check_thread.start()
        
    def create_playlist(self, name: str) -> bool:
        """创建新的播放列表
        
        Args:
            name: 播放列表名称
            
        Returns:
            是否创建成功
        """
        if name in self.playlists:
            return False
            
        self.playlists[name] = []
        self._save_playlists()
        return True
        
    def delete_playlist(self, name: str) -> bool:
        """删除播放列表
        
        Args:
            name: 播放列表名称
            
        Returns:
            是否删除成功
        """
        if name not in self.playlists:
            return False
            
        del self.playlists[name]
        self._save_playlists()
        return True
        
    def rename_playlist(self, old_name: str, new_name: str) -> bool:
        """重命名播放列表
        
        Args:
            old_name: 原播放列表名称
            new_name: 新播放列表名称
            
        Returns:
            是否重命名成功
        """
        if old_name not in self.playlists or new_name in self.playlists:
            return False
            
        self.playlists[new_name] = self.playlists.pop(old_name)
        self._save_playlists()
        return True
        
    def add_to_playlist(self, playlist_name: str, files: List[Dict]) -> bool:
        """向播放列表添加文件
        
        Args:
            playlist_name: 播放列表名称
            files: 要添加的文件列表
            
        Returns:
            是否添加成功
        """
        if playlist_name not in self.playlists:
            return False
            
        # 检查文件是否已存在
        existing_paths = {f['path'] for f in self.playlists[playlist_name]}
        new_files = [f for f in files if f['path'] not in existing_paths]
        
        if new_files:
            self.playlists[playlist_name].extend(new_files)
            self._save_playlists()
            
        return True
        
    def remove_from_playlist(self, playlist_name: str, indices: List[int]) -> bool:
        """从播放列表移除文件
        
        Args:
            playlist_name: 播放列表名称
            indices: 要移除的文件索引列表
            
        Returns:
            是否移除成功
        """
        if playlist_name not in self.playlists:
            return False
            
        # 按索引从大到小排序，以避免删除时影响其他索引
        indices.sort(reverse=True)
        
        for index in indices:
            if 0 <= index < len(self.playlists[playlist_name]):
                self.playlists[playlist_name].pop(index)
                
        self._save_playlists()
        return True
        
    def reorder_playlist(self, playlist_name: str, from_index: int, to_index: int) -> bool:
        """重新排序播放列表中的文件
        
        Args:
            playlist_name: 播放列表名称
            from_index: 原始位置
            to_index: 目标位置
            
        Returns:
            是否重排成功
        """
        if playlist_name not in self.playlists:
            return False
            
        playlist = self.playlists[playlist_name]
        if not (0 <= from_index < len(playlist) and 0 <= to_index < len(playlist)):
            return False
            
        item = playlist.pop(from_index)
        playlist.insert(to_index, item)
        
        self._save_playlists()
        return True
        
    def get_playlist(self, name: str) -> Optional[List[Dict]]:
        """获取播放列表
        
        Args:
            name: 播放列表名称
            
        Returns:
            播放列表内容，如果不存在返回None
        """
        return self.playlists.get(name)
        
    def get_all_playlists(self) -> Dict[str, List[Dict]]:
        """获取所有播放列表
        
        Returns:
            所有播放列表的字典
        """
        return self.playlists.copy()
        
    def add_to_recent(self, file_info: Dict) -> None:
        """添加文件到最近播放列表
        
        Args:
            file_info: 文件信息
        """
        # 如果文件已在最近播放列表中，先移除它
        self.recent_played = deque(
            [f for f in self.recent_played if f['path'] != file_info['path']],
            maxlen=30
        )
        
        # 添加到最近播放列表开头
        self.recent_played.appendleft(file_info)
        self._save_recent_played()
        
    def get_recent_played(self) -> List[Dict]:
        """获取最近播放列表
        
        Returns:
            最近播放列表
        """
        return list(self.recent_played)
        
    def check_file_validity(self, file_info: Dict) -> bool:
        """检查文件是否有效
        
        Args:
            file_info: 文件信息
            
        Returns:
            文件是否有效
        """
        path = file_info['path']
        
        # 检查缓存
        if path in self.url_cache:
            cache_info = self.url_cache[path]
            # 如果缓存未过期，直接返回
            if time.time() - cache_info['timestamp'] < self.url_check_interval:
                return cache_info['valid']
                
        try:
            # 通过API验证文件
            self.api_client.get_file_download_url(path)
            self.url_cache[path] = {
                'valid': True,
                'timestamp': time.time()
            }
            return True
        except:
            self.url_cache[path] = {
                'valid': False,
                'timestamp': time.time()
            }
            return False
            
    def _load_playlists(self) -> None:
        """从文件加载播放列表"""
        try:
            playlist_file = os.path.join(self.data_dir, "playlists.json")
            if os.path.exists(playlist_file):
                with open(playlist_file, 'r', encoding='utf-8') as f:
                    self.playlists = json.load(f)
                    
            recent_file = os.path.join(self.data_dir, "recent.json")
            if os.path.exists(recent_file):
                with open(recent_file, 'r', encoding='utf-8') as f:
                    recent_list = json.load(f)
                    self.recent_played = deque(recent_list, maxlen=30)
        except Exception as e:
            print(f"加载播放列表失败: {str(e)}")
            self.playlists = {}
            self.recent_played.clear()
            
    def _save_playlists(self) -> None:
        """保存播放列表到文件"""
        try:
            playlist_file = os.path.join(self.data_dir, "playlists.json")
            with open(playlist_file, 'w', encoding='utf-8') as f:
                json.dump(self.playlists, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存播放列表失败: {str(e)}")
            
    def _save_recent_played(self) -> None:
        """保存最近播放列表到文件"""
        try:
            recent_file = os.path.join(self.data_dir, "recent.json")
            with open(recent_file, 'w', encoding='utf-8') as f:
                json.dump(list(self.recent_played), f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存最近播放列表失败: {str(e)}")
            
    def _url_check_loop(self) -> None:
        """URL有效性检查循环"""
        while True:
            # 遍历所有播放列表中的文件
            for playlist in self.playlists.values():
                for file_info in playlist:
                    self.check_file_validity(file_info)
                    
            # 检查最近播放列表
            for file_info in self.recent_played:
                self.check_file_validity(file_info)
                
            # 等待下一次检查
            time.sleep(self.url_check_interval)
