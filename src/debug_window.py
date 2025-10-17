import threading
import datetime
import logging
import time
import os

# 尝试导入tkinter，如果失败则使用控制台模式
try:
    import tkinter as tk
    from tkinter import ttk
    TKINTER_AVAILABLE = True
except ImportError as e:
    TKINTER_AVAILABLE = False
    logging.warning(f"无法导入tkinter: {e}")

class DebugWindow:
    def __init__(self, debug_data, debug_data_lock, cmd_log_list, cmd_log_list_lock):
        self.debug_data = debug_data
        self.debug_data_lock = debug_data_lock
        self.cmd_log_list = cmd_log_list
        self.cmd_log_list_lock = cmd_log_list_lock
        self.root = None
        self.is_running = True
        
        if not TKINTER_AVAILABLE:
            logging.info("使用控制台Debug模式")
            self.console_mode = True
            return
            
        self.console_mode = False
        
        try:
            self.root = tk.Tk()
            self.root.title("🎵 AutoDori Debug 面板")
            self.root.geometry("500x500")
            self.root.resizable(True, True)
            
            # 设置窗口关闭事件
            self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
            
            # 创建基本UI
            self.setup_ui()
            
            # 初始更新
            self.update_display()
            
            logging.info("🎵 Debug窗口创建成功")
            
        except Exception as e:
            logging.error(f"创建debug窗口失败: {e}")
            self.console_mode = True
            self.is_running = False
            if self.root:
                self.root.destroy()
            self.root = None
    
    def setup_ui(self):
        """设置UI"""
        try:
            # 简单的UI设置
            self.root.configure(bg='white')
            
            # 标题
            title_label = tk.Label(self.root, text="🎵 AutoDori Debug 面板", 
                                 font=('Arial', 14, 'bold'), bg='white')
            title_label.pack(pady=10)
            
            # 状态框架
            status_frame = tk.Frame(self.root, bg='white')
            status_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
            
            # 状态标签
            self.status_labels = {}
            fields = [
                ("歌曲名称:", "song_name"),
                ("当前任务:", "current_task"), 
                ("程序状态:", "status"),
                ("LiveBoost:", "remaining_liveboost"),
                ("失败次数:", "play_failed_times"),
                ("最后更新:", "last_update")
            ]
            
            for i, (label_text, key) in enumerate(fields):
                tk.Label(status_frame, text=label_text, font=('Arial', 10, 'bold'), 
                        bg='white', anchor='w').grid(row=i, column=0, sticky='w', pady=2)
                label = tk.Label(status_frame, text="", font=('Arial', 10), 
                               bg='white', anchor='w')
                label.grid(row=i, column=1, sticky='w', pady=2)
                self.status_labels[key] = label
            
            # 偏移量标签
            tk.Label(status_frame, text="偏移量:", font=('Arial', 10, 'bold'), 
                    bg='white', anchor='w').grid(row=len(fields), column=0, sticky='w', pady=2)
            self.offset_label = tk.Label(status_frame, text="", font=('Arial', 9), 
                                       bg='white', anchor='w', justify='left')
            self.offset_label.grid(row=len(fields), column=1, sticky='w', pady=2)
            
            # 日志区域
            log_frame = tk.Frame(self.root, bg='white')
            log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
            
            tk.Label(log_frame, text="命令日志:", font=('Arial', 10, 'bold'), 
                    bg='white').pack(anchor='w')
            
            self.log_text = tk.Text(log_frame, height=10, width=60, 
                                  bg='#f0f0f0', fg='black')
            scrollbar = tk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
            self.log_text.configure(yscrollcommand=scrollbar.set)
            
            self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
        except Exception as e:
            logging.error(f"设置UI失败: {e}")
            raise
    
    def on_closing(self):
        """窗口关闭事件"""
        self.is_running = False
        if self.root:
            self.root.destroy()
        logging.info("🎵 Debug窗口已关闭")
    
    def update_display(self):
        """更新显示"""
        if self.console_mode:
            self.update_console()
            return
            
        if not self.root or not self.is_running:
            return
            
        try:
            # 获取数据
            data = {}
            if self.debug_data_lock.acquire(timeout=0.5):
                try:
                    data = self.debug_data.copy()
                finally:
                    self.debug_data_lock.release()
            
            # 更新标签
            for key, label in self.status_labels.items():
                value = data.get(key, "")
                if key == "play_failed_times":
                    value = str(value)
                label.config(text=value or "未知")
            
            # 更新偏移量
            offset = data.get("offset", {})
            offset_text = f"up: {offset.get('up', 0)}, down: {offset.get('down', 0)}, move: {offset.get('move', 0)}\n"
            offset_text += f"wait: {offset.get('wait', 0):.3f}, interval: {offset.get('interval', 0):.3f}"
            self.offset_label.config(text=offset_text)
            
            # 更新日志
            if self.cmd_log_list_lock.acquire(timeout=0.5):
                try:
                    current_count = len(self.cmd_log_list)
                    if hasattr(self, 'last_log_count') and current_count > self.last_log_count:
                        new_logs = self.cmd_log_list[self.last_log_count:]
                        for log in new_logs:
                            timestamp = datetime.datetime.now().strftime("%H:%M:%S")
                            self.log_text.insert(tk.END, f"[{timestamp}] {log.cmd}\n")
                        self.log_text.see(tk.END)
                    self.last_log_count = current_count
                finally:
                    self.cmd_log_list_lock.release()
            
            # 继续更新
            if self.is_running:
                self.root.after(1000, self.update_display)
                
        except Exception as e:
            logging.error(f"更新显示失败: {e}")
            if self.is_running:
                self.root.after(1000, self.update_display)
    
    def update_console(self):
        """控制台模式更新"""
        if not self.is_running:
            return
            
        try:
            data = {}
            if self.debug_data_lock.acquire(timeout=0.5):
                try:
                    data = self.debug_data.copy()
                finally:
                    self.debug_data_lock.release()
            
            # 清屏并显示信息
            os.system('cls' if os.name == 'nt' else 'clear')
            print("🎵 AutoDori Debug 信息")
            print("=" * 50)
            print(f"歌曲名称: {data.get('song_name', '未知')}")
            print(f"当前任务: {data.get('current_task', '未知')}")
            print(f"程序状态: {data.get('status', '未知')}")
            print(f"LiveBoost: {data.get('remaining_liveboost', '未知')}")
            print(f"失败次数: {data.get('play_failed_times', 0)}")
            print(f"最后更新: {data.get('last_update', '未知')}")
            
            offset = data.get("offset", {})
            print(f"偏移量: up={offset.get('up', 0)}, down={offset.get('down', 0)}, move={offset.get('move', 0)}")
            print(f"         wait={offset.get('wait', 0):.3f}, interval={offset.get('interval', 0):.3f}")
            
            print("\n最近命令:")
            if self.cmd_log_list_lock.acquire(timeout=0.5):
                try:
                    recent_logs = self.cmd_log_list[-5:]
                    for log in recent_logs:
                        print(f"  {log.cmd} (耗时: {log.cost}ms)")
                finally:
                    self.cmd_log_list_lock.release()
            
            print("\n" + "=" * 50)
            print("按 Ctrl+C 退出")
            
            # 继续更新
            if self.is_running:
                threading.Timer(2, self.update_console).start()
                
        except Exception as e:
            logging.error(f"控制台更新失败: {e}")
            if self.is_running:
                threading.Timer(2, self.update_console).start()
    
    def run(self):
        """运行debug窗口"""
        if self.console_mode:
            logging.info("启动控制台Debug模式")
            try:
                self.update_console()
            except KeyboardInterrupt:
                self.is_running = False
                logging.info("用户中断Debug模式")
            return
            
        try:
            if self.root and self.is_running:
                logging.info("🎵 启动Debug窗口")
                self.root.mainloop()
        except Exception as e:
            logging.error(f"Debug窗口运行错误: {e}")
        finally:
            self.is_running = False

def start_debug_window(debug_data, debug_data_lock, cmd_log_list, cmd_log_list_lock):
    """启动debug窗口（在新线程中运行）"""
    try:
        logging.info("开始创建Debug窗口")
        window = DebugWindow(debug_data, debug_data_lock, cmd_log_list, cmd_log_list_lock)
        if window.root:
            # 在新线程中运行窗口主循环
            window.run()
        else:
            logging.error("Debug窗口创建失败")
    except Exception as e:
        logging.error(f"启动debug窗口失败: {e}")