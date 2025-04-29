import wx
import wx.lib.agw.customtreectrl as CT
from src.api import BaiduPanAPI

class FileBrowser(wx.Panel):
    def __init__(self, parent, api_client):
        super().__init__(parent)
        
        # 使用传入的API客户端
        self.api = api_client
        
        # 存储文件数据的列表
        self.file_data = []
        
        # 创建界面
        self._init_ui()
        
        # 绑定事件
        self._bind_events()
        
        # 加载根目录
        self.load_root_directory()
        
    def _init_ui(self):
        """初始化界面"""
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # 创建工具栏
        toolbar = wx.Panel(self)
        toolbar_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        # 刷新按钮
        self.refresh_btn = wx.Button(toolbar, label="刷新")
        toolbar_sizer.Add(self.refresh_btn, 0, wx.ALL, 5)
        
        # 过滤输入框
        self.filter_text = wx.TextCtrl(toolbar)
        self.filter_text.SetHint("输入过滤条件")
        toolbar_sizer.Add(self.filter_text, 1, wx.ALL | wx.EXPAND, 5)
        
        toolbar.SetSizer(toolbar_sizer)
        main_sizer.Add(toolbar, 0, wx.EXPAND)
        
        # 创建分割窗口
        self.splitter = wx.SplitterWindow(self)
        
        # 创建目录树
        self.tree = CT.CustomTreeCtrl(
            self.splitter,
            agwStyle=CT.TR_DEFAULT_STYLE | CT.TR_HIDE_ROOT | CT.TR_HAS_BUTTONS
        )
        self.root = self.tree.AddRoot("百度云盘")
        
        # 创建文件列表
        self.list = wx.ListCtrl(
            self.splitter,
            style=wx.LC_REPORT | wx.BORDER_SUNKEN | wx.LC_SORT_ASCENDING
        )
        
        # 设置列
        self.list.InsertColumn(0, "文件名", width=200)
        self.list.InsertColumn(1, "大小", width=100)
        self.list.InsertColumn(2, "修改时间", width=150)
        
        # 设置分割窗口
        self.splitter.SplitVertically(self.tree, self.list)
        self.splitter.SetMinimumPaneSize(100)
        self.splitter.SetSashPosition(200)
        
        main_sizer.Add(self.splitter, 1, wx.EXPAND)
        
        # 创建状态栏
        self.status_bar = wx.StatusBar(self)
        self.status_bar.SetFieldsCount(2)
        self.status_bar.SetStatusWidths([-2, -1])
        main_sizer.Add(self.status_bar, 0, wx.EXPAND)
        
        self.SetSizer(main_sizer)
        
    def _bind_events(self):
        """绑定事件处理"""
        # 目录树事件
        self.tree.Bind(wx.EVT_TREE_ITEM_EXPANDING, self.on_item_expanding)
        self.tree.Bind(wx.EVT_TREE_SEL_CHANGED, self.on_sel_changed)
        
        # 文件列表事件
        self.list.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.on_item_activated)
        self.list.Bind(wx.EVT_LIST_ITEM_RIGHT_CLICK, self.on_item_right_click)
        
        # 工具栏事件
        self.refresh_btn.Bind(wx.EVT_BUTTON, self.on_refresh)
        self.filter_text.Bind(wx.EVT_TEXT, self.on_filter)
        
    def load_root_directory(self):
        """加载根目录"""
        try:
            # 显示加载状态
            self.status_bar.SetStatusText("正在加载根目录...", 0)
            wx.BeginBusyCursor()
            
            # 获取根目录文件列表
            files = self.api.list_files("/")
            
            # 恢复光标
            wx.EndBusyCursor()
            
            # 清空目录树
            self.tree.DeleteChildren(self.root)
            
            # 添加文件夹到目录树
            for file in files:
                if file['isdir'] == 1:
                    child = self.tree.AppendItem(self.root, file['server_filename'])
                    self.tree.SetItemData(child, file)
                    # 添加临时子项以显示展开按钮
                    self.tree.AppendItem(child, "")
                    
            self.status_bar.SetStatusText(f"加载了 {len(files)} 个项目")
            
        except Exception as e:
            wx.MessageBox(f"加载目录失败: {str(e)}", "错误", wx.OK | wx.ICON_ERROR)
            
    def on_item_expanding(self, event):
        """处理目录展开事件"""
        item = event.GetItem()
        
        # 如果只有一个空的子项，则加载子目录
        if self.tree.GetChildrenCount(item) == 1:
            first_child = self.tree.GetFirstChild(item)[0]
            if not self.tree.GetItemText(first_child):
                # 获取当前项的数据
                data = self.tree.GetItemData(item)
                if data:
                    try:
                        # 获取子目录文件列表
                        files = self.api.list_files(data['path'])
                        
                        # 删除临时子项
                        self.tree.DeleteChildren(item)
                        
                        # 添加文件夹到目录树
                        for file in files:
                            if file['isdir'] == 1:
                                child = self.tree.AppendItem(item, file['server_filename'])
                                self.tree.SetItemData(child, file)
                                # 添加临时子项以显示展开按钮
                                self.tree.AppendItem(child, "")
                                
                    except Exception as e:
                        wx.MessageBox(f"加载子目录失败: {str(e)}", "错误", 
                                    wx.OK | wx.ICON_ERROR)
                        
    def on_sel_changed(self, event):
        """处理目录选择变更事件"""
        item = event.GetItem()
        data = self.tree.GetItemData(item)
        
        if data:
            try:
                # 显示加载状态
                self.status_bar.SetStatusText(f"正在加载 {data['path']}...", 0)
                wx.BeginBusyCursor()
                
                # 获取当前目录的文件列表
                files = self.api.list_files(data['path'])
                
                # 恢复光标
                wx.EndBusyCursor()
                
                # 更新文件列表
                self.update_file_list(files)
                
            except Exception as e:
                wx.MessageBox(f"加载文件列表失败: {str(e)}", "错误", 
                            wx.OK | wx.ICON_ERROR)
                
    def update_file_list(self, files):
        """更新文件列表"""
        # 显示加载状态
        self.status_bar.SetStatusText("正在更新文件列表...", 0)
        wx.BeginBusyCursor()
        
        # 清空列表和数据
        self.list.DeleteAllItems()
        self.file_data = []
        
        # 获取过滤文本
        filter_text = self.filter_text.GetValue().lower()
        
        # 音频文件扩展名
        audio_exts = {'.mp3', '.wav', '.flac', '.m4a', '.ogg', '.wma'}
        
        # 添加文件到列表
        count = 0
        for file in files:
            # 跳过目录
            if file['isdir'] == 1:
                continue
                
            # 检查是否为音频文件
            ext = '.' + file['server_filename'].split('.')[-1].lower()
            if ext not in audio_exts:
                continue
                
            # 应用过滤
            if filter_text and filter_text not in file['server_filename'].lower():
                continue
                
            # 添加到列表
            index = self.list.GetItemCount()
            self.list.InsertItem(index, file['server_filename'])
            self.list.SetItem(index, 1, str(self._format_size(file['size'])))
            self.list.SetItem(index, 2, str(file['server_mtime']))
            
            # 存储文件数据并设置索引
            self.file_data.append(file)
            self.list.SetItemData(index, len(self.file_data) - 1)
            count += 1
            
        # 更新状态栏
        total_size = sum(file['size'] for file in files if file['isdir'] == 0)
        self.status_bar.SetStatusText(f"显示 {count} 个音频文件", 0)
        self.status_bar.SetStatusText(f"总大小: {self._format_size(total_size)}", 1)
        
        # 恢复光标
        wx.EndBusyCursor()
        
    def _format_size(self, size):
        """格式化文件大小显示"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"
        
    def get_selected_files(self):
        """获取选中的文件列表"""
        selected_files = []
        item = -1
        while True:
            item = self.list.GetNextItem(item, wx.LIST_NEXT_ALL, wx.LIST_STATE_SELECTED)
            if item == -1:
                break
            data_index = self.list.GetItemData(item)
            selected_files.append(self.file_data[data_index])
        return selected_files

    def get_directory_files(self, path):
        """递归获取目录下的所有音频文件"""
        audio_files = []
        try:
            files = self.api.list_files(path)
            for file in files:
                if file['isdir'] == 1:
                    # 递归获取子目录的文件
                    audio_files.extend(self.get_directory_files(file['path']))
                else:
                    # 检查是否为音频文件
                    ext = '.' + file['server_filename'].split('.')[-1].lower()
                    if ext in {'.mp3', '.wav', '.flac', '.m4a', '.ogg', '.wma'}:
                        audio_files.append(file)
        except Exception as e:
            wx.MessageBox(f"获取目录 {path} 的文件失败: {str(e)}", "错误", wx.OK | wx.ICON_ERROR)
        return audio_files

    def on_item_activated(self, event):
        """处理文件双击事件"""
        selected_files = self.get_selected_files()
        if selected_files:
            # 发送添加到播放列表的事件
            evt = wx.CommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED)
            evt.SetEventObject(self)
            evt.SetId(wx.ID_ADD)
            evt.SetClientData(selected_files)
            wx.PostEvent(self, evt)
            
    def on_item_right_click(self, event):
        """处理文件右键点击事件"""
        # 创建右键菜单
        menu = wx.Menu()
        
        # 添加菜单项
        add_item = menu.Append(wx.ID_ADD, "添加到播放列表")
        add_dir_item = menu.Append(wx.ID_ANY, "添加文件夹到播放列表")
        
        # 绑定事件
        menu.Bind(wx.EVT_MENU, self.on_add_to_playlist, add_item)
        menu.Bind(wx.EVT_MENU, self.on_add_directory_to_playlist, add_dir_item)
        
        # 显示菜单
        self.PopupMenu(menu)
        menu.Destroy()
        
    def on_add_to_playlist(self, event):
        """处理添加到播放列表事件"""
        selected_files = self.get_selected_files()
        if selected_files:
            # 发送添加到播放列表的事件
            evt = wx.CommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED)
            evt.SetEventObject(self)
            evt.SetId(wx.ID_ADD)
            evt.SetClientData(selected_files)
            wx.PostEvent(self, evt)
            
    def on_add_directory_to_playlist(self, event):
        """处理添加文件夹到播放列表事件"""
        item = self.tree.GetSelection()
        if item.IsOk():
            data = self.tree.GetItemData(item)
            if data:
                # 获取目录下所有音频文件
                audio_files = self.get_directory_files(data['path'])
                if audio_files:
                    # 发送添加到播放列表的事件
                    evt = wx.CommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED)
                    evt.SetEventObject(self)
                    evt.SetId(wx.ID_ADD)
                    evt.SetClientData(audio_files)
                    wx.PostEvent(self, evt)
                else:
                    wx.MessageBox("未在该目录下找到音频文件", "提示", wx.OK | wx.ICON_INFORMATION)
            
    def on_refresh(self, event):
        """处理刷新按钮事件"""
        # 重新加载当前选中的目录
        item = self.tree.GetSelection()
        if item.IsOk():
            data = self.tree.GetItemData(item)
            if data:
                try:
                    files = self.api.list_files(data['path'])
                    self.update_file_list(files)
                except Exception as e:
                    wx.MessageBox(f"刷新文件列表失败: {str(e)}", "错误", 
                                wx.OK | wx.ICON_ERROR)
                                
    def on_filter(self, event):
        """处理过滤文本变更事件"""
        # 重新加载当前文件列表
        item = self.tree.GetSelection()
        if item.IsOk():
            data = self.tree.GetItemData(item)
            if data:
                try:
                    files = self.api.list_files(data['path'])
                    self.update_file_list(files)
                except Exception as e:
                    wx.MessageBox(f"更新文件列表失败: {str(e)}", "错误", 
                                wx.OK | wx.ICON_ERROR)
