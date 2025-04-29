import wx
import wx.dataview as dv
from src.playlist import PlaylistManager

class PlaylistPanel(wx.Panel):
    def __init__(self, parent, api_client):
        super().__init__(parent)
        
        # 初始化播放列表管理器和播放器
        self.playlist_manager = PlaylistManager(api_client)
        self.player = None
        
        # 创建界面
        self._init_ui()
        
        # 绑定事件
        self._bind_events()
        
    def set_player(self, player):
        """设置播放器实例"""
        self.player = player
        
    def _init_ui(self):
        """初始化界面"""
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # 创建工具栏
        toolbar = wx.ToolBar(self)
        new_list_tool = toolbar.AddTool(wx.ID_ANY, "新建列表", 
            wx.ArtProvider.GetBitmap(wx.ART_NEW, wx.ART_TOOLBAR))
        delete_list_tool = toolbar.AddTool(wx.ID_ANY, "删除列表",
            wx.ArtProvider.GetBitmap(wx.ART_DELETE, wx.ART_TOOLBAR))
        rename_list_tool = toolbar.AddTool(wx.ID_ANY, "重命名",
            wx.ArtProvider.GetBitmap(wx.ART_EDIT, wx.ART_TOOLBAR))
        toolbar.Realize()
        main_sizer.Add(toolbar, 0, wx.EXPAND)
        
        # 创建播放列表树
        self.playlist_tree = dv.DataViewTreeCtrl(self)
        main_sizer.Add(self.playlist_tree, 1, wx.EXPAND | wx.ALL, 5)
        
        # 创建根节点
        self.root = self.playlist_tree.AppendContainer(dv.NullDataViewItem, "播放列表")
        self.recent_root = self.playlist_tree.AppendContainer(dv.NullDataViewItem, "最近播放")
        
        # 加载播放列表
        self._load_playlists()
        
        self.SetSizer(main_sizer)
        
    def _bind_events(self):
        """绑定事件处理"""
        # 工具栏事件
        self.Bind(wx.EVT_TOOL, self.on_new_playlist, id=wx.ID_ANY)
        self.Bind(wx.EVT_TOOL, self.on_delete_playlist, id=wx.ID_ANY)
        self.Bind(wx.EVT_TOOL, self.on_rename_playlist, id=wx.ID_ANY)
        
        # 树控件事件
        self.playlist_tree.Bind(dv.EVT_DATAVIEW_ITEM_START_EDITING, 
                              self.on_start_editing)
        self.playlist_tree.Bind(dv.EVT_DATAVIEW_ITEM_ACTIVATED,
                              self.on_item_activated)
        self.playlist_tree.Bind(dv.EVT_DATAVIEW_ITEM_BEGIN_DRAG,
                              self.on_begin_drag)
        self.playlist_tree.Bind(dv.EVT_DATAVIEW_ITEM_DROP,
                              self.on_drop)
        
    def _load_playlists(self):
        """加载所有播放列表"""
        # 清空现有列表
        self.playlist_tree.DeleteChildren(self.root)
        self.playlist_tree.DeleteChildren(self.recent_root)
        
        # 加载用户播放列表
        playlists = self.playlist_manager.get_all_playlists()
        for playlist_name in playlists.keys():
            self.playlist_tree.AppendItem(self.root, playlist_name)
            
        # 加载最近播放列表
        recent_tracks = self.playlist_manager.get_recent_played()
        for track in recent_tracks:
            self.playlist_tree.AppendItem(self.recent_root, track['server_filename'])
            
    def on_new_playlist(self, event):
        """创建新播放列表"""
        dialog = wx.TextEntryDialog(self, "请输入播放列表名称：", "新建播放列表")
        if dialog.ShowModal() == wx.ID_OK:
            name = dialog.GetValue().strip()
            if name:
                self.playlist_manager.create_playlist(name)
                self._load_playlists()
        dialog.Destroy()
        
    def on_delete_playlist(self, event):
        """删除播放列表"""
        item = self.playlist_tree.GetSelection()
        if not item.IsOk():
            return
            
        # 确保选中的是播放列表而不是根节点
        parent = self.playlist_tree.GetItemParent(item)
        if parent != self.root:
            return
            
        name = self.playlist_tree.GetItemText(item)
        if wx.MessageBox(f"确定要删除播放列表 '{name}' 吗？", 
                        "确认删除",
                        wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION) == wx.YES:
            self.playlist_manager.delete_playlist(name)
            self._load_playlists()
            
    def on_rename_playlist(self, event):
        """重命名播放列表"""
        item = self.playlist_tree.GetSelection()
        if not item.IsOk():
            return
            
        # 确保选中的是播放列表而不是根节点
        parent = self.playlist_tree.GetItemParent(item)
        if parent != self.root:
            return
            
        old_name = self.playlist_tree.GetItemText(item)
        dialog = wx.TextEntryDialog(self, 
                                  "请输入新的播放列表名称：", 
                                  "重命名播放列表",
                                  old_name)
        if dialog.ShowModal() == wx.ID_OK:
            new_name = dialog.GetValue().strip()
            if new_name and new_name != old_name:
                self.playlist_manager.rename_playlist(old_name, new_name)
                self._load_playlists()
        dialog.Destroy()
        
    def on_start_editing(self, event):
        """开始编辑项目时的处理"""
        item = event.GetItem()
        parent = self.playlist_tree.GetItemParent(item)
        # 只允许编辑播放列表名称，不允许编辑根节点和最近播放
        if parent != self.root:
            event.Veto()
            
    def on_item_activated(self, event):
        """双击项目时的处理"""
        item = event.GetItem()
        if not item.IsOk():
            return
            
        # 获取项目文本和父节点
        text = self.playlist_tree.GetItemText(item)
        parent = self.playlist_tree.GetItemParent(item)
        
        # 根据不同类型的项目执行不同的操作
        if parent == self.root:
            # 播放列表项目：加载并显示播放列表内容
            self.load_playlist_content(text)
        elif parent == self.recent_root:
            # 最近播放项目：直接播放该曲目
            self.play_track(text)
            
    def load_playlist_content(self, playlist_name):
        """加载并显示播放列表内容"""
        playlist = self.playlist_manager.get_playlist(playlist_name)
        if playlist:
            # 获取父窗口（MainWindow）
            main_window = self.GetTopLevelParent()
            content_panel = main_window.content_panel
            
            # 显示内容面板
            pane = main_window._mgr.GetPane("content")
            if not pane.IsShown():
                pane.Show()
            main_window._mgr.Update()
            
            # 清空列表和数据
            content_panel.list.DeleteAllItems()
            content_panel.file_data = []
            
            # 更新列表标题
            for col, title in enumerate(["歌曲名称", "大小", "修改时间"]):
                item = wx.ListItem()
                item.SetText(title)
                content_panel.list.SetColumn(col, item)
            
            for track in playlist:
                index = content_panel.list.GetItemCount()
                content_panel.list.InsertItem(index, track['server_filename'])
                content_panel.list.SetItem(index, 1, content_panel._format_size(track['size']))
                # 格式化时间戳为易读格式
                timestamp = track['server_mtime']
                time_str = wx.DateTime.FromTimeT(timestamp).Format('%Y-%m-%d %H:%M:%S')
                content_panel.list.SetItem(index, 2, time_str)
                # 存储文件数据并设置索引
                content_panel.file_data.append(track)
                content_panel.list.SetItemData(index, len(content_panel.file_data) - 1)
                
            # 更新状态栏
            total_size = sum(track['size'] for track in playlist)
            content_panel.status_bar.SetStatusText(f"播放列表 '{playlist_name}' - {len(playlist)} 个音频文件", 0)
            content_panel.status_bar.SetStatusText(f"总大小: {content_panel._format_size(total_size)}", 1)
            
            # 解绑原有的双击事件（如果存在）
            if hasattr(content_panel.list, 'play_handler_bound'):
                content_panel.list.Unbind(wx.EVT_LIST_ITEM_ACTIVATED)
            
            # 绑定双击播放事件
            content_panel.list.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.on_list_item_activated)
            content_panel.list.play_handler_bound = True
        
    def on_list_item_activated(self, event):
        """处理列表项目双击事件"""
        if self.player:
            index = event.GetIndex()
            main_window = self.GetTopLevelParent()
            content_panel = main_window.content_panel
            if 0 <= index < len(content_panel.file_data):
                track = content_panel.file_data[index]
                # 直接播放文件
                if self.player.load_file(track):
                    self.player.play()
                    # 更新播放器面板显示
                    main_window.control_panel.update_track_info({
                        'name': track['server_filename'],
                        'artist': '未知艺术家',
                        'album': '未知专辑'
                    })
                    # 添加到最近播放列表
                    self.playlist_manager.add_to_recent(track)
                    self.refresh()

    def play_track(self, track_name):
        """播放指定曲目"""
        if self.player:
            # 在最近播放列表中查找曲目
            recent_tracks = self.playlist_manager.get_recent_played()
            for track in recent_tracks:
                if track['server_filename'] == track_name:
                    # 获取播放URL并播放
                    if self.player.load_file(track):
                        self.player.play()
                        # 更新播放器面板显示
                        main_window = self.GetTopLevelParent()
                        main_window.control_panel.update_track_info(track)
                    break
        
    def add_file(self, file_info_list):
        """添加文件到播放列表
        
        Args:
            file_info_list: 文件信息字典列表
        """
        # 获取所有播放列表名称
        playlists = list(self.playlist_manager.get_all_playlists().keys())
        
        if not playlists:
            # 如果没有播放列表，先创建一个
            if wx.MessageBox("没有可用的播放列表，是否创建新播放列表？",
                           "添加到播放列表",
                           wx.YES_NO | wx.YES_DEFAULT | wx.ICON_QUESTION) == wx.YES:
                dialog = wx.TextEntryDialog(self, "请输入播放列表名称：", "新建播放列表")
                if dialog.ShowModal() == wx.ID_OK:
                    name = dialog.GetValue().strip()
                    if name:
                        self.playlist_manager.create_playlist(name)
                        playlists = [name]
                    else:
                        return
                dialog.Destroy()
            else:
                return
        
        # 让用户选择播放列表
        dialog = wx.SingleChoiceDialog(self,
                                     "请选择要添加到的播放列表：",
                                     "添加到播放列表",
                                     playlists)
        
        if dialog.ShowModal() == wx.ID_OK:
            playlist_name = dialog.GetStringSelection()
            # 添加文件到播放列表
            if isinstance(file_info_list, list):
                self.playlist_manager.add_to_playlist(playlist_name, file_info_list)
            else:
                self.playlist_manager.add_to_playlist(playlist_name, [file_info_list])
            # 刷新显示
            self._load_playlists()
            
        dialog.Destroy()
        
    def refresh(self):
        """刷新播放列表显示"""
        self._load_playlists()
        
    def on_begin_drag(self, event):
        """开始拖拽时的处理"""
        item = event.GetItem()
        if not item.IsOk():
            event.Veto()
            return
            
        # 只允许拖拽播放列表中的项目
        parent = self.playlist_tree.GetItemParent(item)
        if parent != self.root:
            event.Veto()
            return
            
        event.Allow()
        
    def on_drop(self, event):
        """处理拖放事件"""
        item = event.GetItem()
        if not item.IsOk():
            event.Veto()
            return
            
        # 获取拖拽的源项目和目标项目
        drag_item = event.GetDragItem()
        if not drag_item.IsOk():
            event.Veto()
            return
            
        # 确保源项目和目标项目都在播放列表根节点下
        parent = self.playlist_tree.GetItemParent(item)
        drag_parent = self.playlist_tree.GetItemParent(drag_item)
        if parent != self.root or drag_parent != self.root:
            event.Veto()
            return
            
        # 获取源和目标的文本
        source_text = self.playlist_tree.GetItemText(drag_item)
        target_text = self.playlist_tree.GetItemText(item)
        
        # 获取源和目标的索引
        source_index = -1
        target_index = -1
        playlist = self.playlist_manager.get_playlist(source_text)
        if playlist:
            source_index = list(self.playlist_manager.playlists.keys()).index(source_text)
            target_index = list(self.playlist_manager.playlists.keys()).index(target_text)
            
            # 调整播放列表顺序
            if source_index != -1 and target_index != -1:
                # 使用playlist_manager的reorder_playlist方法
                self.playlist_manager.reorder_playlist(source_text, source_index, target_index)
                # 刷新显示
                self._load_playlists()
                
        event.Allow()
