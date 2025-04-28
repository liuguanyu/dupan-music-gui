"""
百度云盘音乐播放器认证模块
实现OAuth2.0认证流程和会话管理
"""

import os
import json
import uuid
import requests
import qrcode
from datetime import datetime, timedelta
from PIL import Image
import wx

class AuthManager:
    def __init__(self):
        # 加载配置文件
        try:
            config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.json')
            if not os.path.exists(config_path):
                template_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.template.json')
                raise FileNotFoundError(
                    f"配置文件不存在。请根据{template_path}创建config.json文件"
                )
            
            with open(config_path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
                
            # 添加动态生成的配置
            self.config['device_id'] = str(uuid.uuid4())
        except FileNotFoundError as e:
            raise e
        except json.JSONDecodeError:
            raise ValueError("配置文件格式错误，请检查JSON格式")
        except Exception as e:
            raise ValueError(f"加载配置文件失败: {str(e)}")
        
        self.token_info = None
        self.device_code = None
        self.last_poll_time = 0
        self.poll_interval = 5
        
        # 确保配置目录存在
        self.config_dir = os.path.join(os.path.expanduser('~'), '.config', 'dupan-music')
        self.token_path = os.path.join(self.config_dir, 'token.json')
        os.makedirs(self.config_dir, exist_ok=True)
        
        # 加载已保存的token
        self._load_token()
        
    def get_device_code(self):
        """获取设备码和二维码"""
        url = f"{self.config['oauth_url']}/device/code"
        params = {
            'response_type': 'device_code',
            'client_id': self.config['app_key'],
            'scope': self.config['scope']
        }
        
        try:
            response = requests.get(url, params=params, headers={'User-Agent': 'pan.baidu.com'})
            response.raise_for_status()
            data = response.json()
            
            if 'error' in data:
                raise ValueError(f"获取设备码失败: {data.get('error_description', data['error'])}")
                
            self.device_code = data['device_code']
            self.poll_interval = data.get('interval', 5)
            
            # 确保返回verification_url，如果API没有返回，使用默认值
            if 'verification_url' not in data:
                data['verification_url'] = 'https://openapi.baidu.com/device'
                
            return data
        except Exception as e:
            print(f"获取设备码失败: {e}")
            raise
            
    def show_login_qr(self, parent=None):
        """显示登录二维码"""
        try:
            # 获取设备码和验证URL
            auth_data = self.get_device_code()
            verification_url = auth_data['verification_url']
            user_code = auth_data['user_code']
            
            # 构建完整的验证URL
            qr_url = f"{verification_url}?code={user_code}"
            
            # 如果是在GUI中显示
            if parent and isinstance(parent, wx.Window):
                # 生成二维码
                qr = qrcode.QRCode(
                    version=1,
                    error_correction=qrcode.constants.ERROR_CORRECT_L,
                    box_size=15,
                    border=2,
                )
                qr.add_data(qr_url)
                qr.make(fit=True)
                
                # 创建二维码图片
                qr_image = qr.make_image(fill_color="black", back_color="white")
                
                # 调整图像大小为300x300
                qr_image = qr_image.resize((300, 300), Image.Resampling.LANCZOS)
                
                # 保存为临时文件
                temp_path = os.path.join(os.path.dirname(__file__), "temp_qr.png")
                qr_image.save(temp_path, format='PNG')
                
                # 加载图片并转换为wx.Bitmap
                wx_image = wx.Image(temp_path, wx.BITMAP_TYPE_PNG)
                if wx_image.IsOk():
                    wx_bitmap = wx_image.ConvertToBitmap()
                    # 删除临时文件
                    os.remove(temp_path)
                else:
                    raise ValueError("无法加载二维码图像")
                
                # 更新UI
                if hasattr(parent, 'qr_bitmap'):
                    try:
                        parent.qr_bitmap.SetBitmap(wx_bitmap)
                        parent.Layout()
                    except Exception as e:
                        raise ValueError(f"设置二维码图像失败: {str(e)}")
            else:
                # 不再使用浏览器打开二维码
                pass
        except Exception as e:
            print(f"显示二维码失败: {e}")
            raise
            
    def check_auth_status(self):
        """检查授权状态"""
        if not self.device_code:
            return False
            
        # 更新最后轮询时间
        self.last_poll_time = datetime.now().timestamp()
        
        url = f"{self.config['oauth_url']}/token"
        params = {
            'grant_type': 'device_token',
            'code': self.device_code,
            'client_id': self.config['app_key'],
            'client_secret': self.config['secret_key']
        }
        
        try:
            response = requests.get(url, params=params, headers={'User-Agent': 'pan.baidu.com'})
            data = response.json()
            
            # 成功获取token
            if response.status_code == 200 and 'access_token' in data:
                self.token_info = data
                self._update_token_expiry()
                return True
                
            # 错误状态处理
            error = data.get('error', '')
            
            if error == 'authorization_pending':
                return False  # 等待用户授权
            elif error == 'slow_down':
                # 请求过于频繁，增加轮询间隔
                self.poll_interval = data.get('interval', self.poll_interval + 5)
                return False
            elif error == 'expired_token':
                self.device_code = None  # 重置设备码
                raise ValueError("授权码已过期，请重新获取")
            elif error == 'invalid_grant':
                self.device_code = None  # 重置设备码
                raise ValueError("授权码无效，请重新获取")
            elif error == 'authorization_declined':
                self.device_code = None  # 重置设备码
                raise ValueError("用户拒绝授权")
            elif error == 'access_denied':
                self.device_code = None  # 重置设备码
                raise ValueError("访问被拒绝")
                
            # 其他错误
            if error:
                raise ValueError(f"授权错误: {data.get('error_description', error)}")
                
            return False
        except requests.exceptions.RequestException as e:
            print(f"检查授权状态失败: {e}")
            return False
            
    def _update_token_expiry(self):
        """更新token过期时间"""
        if self.token_info and 'expires_in' in self.token_info:
            expires_in = self.token_info['expires_in']
            self.expires_at = datetime.now() + timedelta(seconds=expires_in)
            self.device_code = None  # 清除设备码
            
    def is_logged_in(self):
        """检查是否已登录"""
        if not self.token_info:
            return False
            
        if self.device_code:
            return self.check_auth_status()
            
        return datetime.now() < self.expires_at if self.expires_at else False
               
    def _save_token(self):
        """保存token到本地文件"""
        try:
            with open(self.token_path, 'w') as f:
                json.dump(self.token_info, f)
            return True
        except Exception as e:
            print(f"保存token失败: {e}")
            return False

    def _load_token(self):
        """从本地文件加载token"""
        try:
            if os.path.exists(self.token_path):
                with open(self.token_path, 'r') as f:
                    self.token_info = json.load(f)
                    if self.token_info:
                        self._update_token_expiry()
                    return True
        except Exception as e:
            print(f"加载token失败: {e}")
        return False

    def clear_token(self):
        """清除token"""
        self.token_info = None
        self.expires_at = None
        try:
            if os.path.exists(self.token_path):
                os.remove(self.token_path)
            return True
        except Exception as e:
            print(f"清除token失败: {e}")
            return False

    def refresh_token(self):
        """刷新token"""
        if not self.token_info or 'refresh_token' not in self.token_info:
            return False
            
        refresh_url = f"{self.config['oauth_url']}/token"
        params = {
            'grant_type': 'refresh_token',
            'refresh_token': self.token_info['refresh_token'],
            'client_id': self.config['app_key'],
            'client_secret': self.config['secret_key']
        }
        
        try:
            response = requests.get(refresh_url, params=params, headers={'User-Agent': 'pan.baidu.com'})
            response.raise_for_status()
            self.token_info = response.json()
            self._update_token_expiry()
            self._save_token()
            return True
        except Exception as e:
            print(f"刷新token失败: {e}")
            return False

    def get_user_info(self):
        """获取用户信息"""
        if not self.token_info or not self.token_info.get('access_token'):
            raise ValueError("未登录，请先登录")

        try:
            response = requests.get(
                f"{self.config['api_base_url']}/xpan/nas",
                params={
                    'method': 'uinfo',
                    'access_token': self.token_info['access_token']
                },
                headers={'User-Agent': 'pan.baidu.com'}
            )
            response.raise_for_status()
            data = response.json()

            if data.get('errno') != 0:
                raise ValueError(f"获取用户信息失败: {data.get('errmsg', '未知错误')}")

            return {
                'uk': data.get('uk'),
                'baiduid': data.get('baidu_name'),
                'username': data.get('netdisk_name') or data.get('baidu_name') or '未知用户',
                'avatarUrl': data.get('avatar_url', ''),
                'vipType': data.get('vip_type'),
                'isVip': data.get('is_vip') == 1
            }
        except Exception as e:
            print(f"获取用户信息失败: {e}")
            raise

if __name__ == '__main__':
    auth = AuthManager()
