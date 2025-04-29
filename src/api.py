import os
import json
import time
import requests
from typing import Dict, List, Optional, Any
from urllib.parse import urlencode

class BaiduPanAPI:
    def __init__(self, auth_manager):
        """初始化百度网盘API客户端
        
        Args:
            auth_manager: 认证管理器实例，用于获取access token
        """
        self.auth_manager = auth_manager
        self.api_base_url = "https://pan.baidu.com/rest/2.0"
        self.cache_dir = os.path.join(os.path.expanduser("~"), ".dupan", "cache")
        os.makedirs(self.cache_dir, exist_ok=True)
        
    def _make_request(self, method: str, endpoint: str, params: Dict = None, data: Dict = None) -> Dict:
        """发送API请求
        
        Args:
            method: HTTP方法
            endpoint: API端点
            params: URL参数
            data: POST数据
            
        Returns:
            API响应数据
        """
        if params is None:
            params = {}
        
        # 添加access_token到参数中
        params['access_token'] = self.auth_manager.get_access_token()
        
        url = f"{self.api_base_url}/{endpoint}"
        response = requests.request(method, url, params=params, json=data)
        
        if response.status_code != 200:
            raise Exception(f"API请求失败: {response.status_code} - {response.text}")
            
        result = response.json()
        if 'errno' in result and result['errno'] != 0:
            raise Exception(f"API错误: {result['errno']} - {result.get('errmsg', '未知错误')}")
            
        return result
        
    def list_files(self, dir_path: str = "/", recursive: bool = False, 
                   file_types: List[str] = None) -> List[Dict]:
        """获取目录下的文件列表
        
        Args:
            dir_path: 目录路径
            recursive: 是否递归获取子目录
            file_types: 文件类型过滤列表
            
        Returns:
            文件列表
        """
        params = {
            'method': 'list',
            'dir': dir_path,
            'web': 'web',
            'order': 'name',
            'desc': 0,
            'start': 0,
            'limit': 1000,
            'folder': 0,
            'showempty': 1
        }
        
        all_files = []
        while True:
            result = self._make_request('GET', 'xpan/file', params=params)
            
            if 'list' not in result:
                break
                
            files = result['list']
            if not files:
                break
                
            for file in files:
                # 如果指定了文件类型过滤，则只返回匹配的文件
                if file_types and file['isdir'] == 0:
                    ext = os.path.splitext(file['server_filename'])[1].lower()
                    if ext not in file_types:
                        continue
                        
                all_files.append(file)
                
                # 如果是目录且需要递归，则获取子目录内容
                if recursive and file['isdir'] == 1:
                    sub_files = self.list_files(file['path'], recursive, file_types)
                    all_files.extend(sub_files)
            
            params['start'] += len(files)
            
            # 如果返回的文件数小于limit，说明已经获取完所有文件
            if len(files) < params['limit']:
                break
                
        return all_files
        
    def get_file_download_url(self, fs_id: int) -> str:
        """获取文件的下载链接
        
        Args:
            fs_id: 文件的fs_id
            
        Returns:
            文件下载链接
        """
        params = {
            'method': 'filemetas',
            'dlink': 1,
            'fsids': f"[{fs_id}]"
        }
        
        result = self._make_request('GET', 'xpan/multimedia', params=params)
        
        if not result.get('list') or len(result['list']) == 0:
            raise Exception(f"无法获取文件下载链接，fs_id: {fs_id}")
            
        dlink = result['list'][0]['dlink']
        
        # 为下载链接添加access_token
        return f"{dlink}&access_token={self.auth_manager.get_access_token()}"
        
    def get_user_info(self) -> Dict:
        """获取用户信息
        
        Returns:
            用户信息字典
        """
        params = {
            'method': 'uinfo'
        }
        return self._make_request('GET', 'xpan/nas', params=params)
        
    def get_quota_info(self) -> Dict:
        """获取用户空间配额信息
        
        Returns:
            空间配额信息字典
        """
        params = {
            'method': 'quota',
            'checkfree': 1
        }
        return self._make_request('GET', 'xpan/nas', params=params)
