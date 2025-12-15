import tkinter as tk
from tkinter import messagebox
import sys
import os
import threading
import ctypes

# 互斥锁名称
MUTEX_NAME = "Global\\QQBot_Instance_Mutex_v1"

def is_already_running():
    kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
    # 创建命名互斥锁
    mutex = kernel32.CreateMutexW(None, False, MUTEX_NAME)
    last_error = ctypes.get_last_error()
    
    # ERROR_ALREADY_EXISTS = 183
    if last_error == 183:
        return True
    return False

class TextRedirector:
    def __init__(self, widget):
        self.widget = widget

    def write(self, str):
        self.widget.after(0, self._write, str)

    def _write(self, str):
        self.widget.insert(tk.END, str)
        self.widget.see(tk.END)
        
    def flush(self):
        pass

class BotGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("QQ Bot 控制台")
        self.root.geometry("600x400")
        
        # Start Button
        self.start_btn = tk.Button(root, text="启动机器人", command=self.start_bot, height=2, width=20)
        self.start_btn.pack(pady=20)
        
        # Log area
        self.log_text = tk.Text(root, height=15)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Redirect stdout
        sys.stdout = TextRedirector(self.log_text)
        sys.stderr = TextRedirector(self.log_text)

    def start_bot(self):
        self.start_btn.config(state=tk.DISABLED, text="正在运行...")
        
        # Run in thread
        t = threading.Thread(target=self.run_bot_thread, daemon=True)
        t.start()

    def run_bot_thread(self):
        try:
            print("正在启动机器人...")
            # Import here to ensure env is loaded by nonebot.init() which happens inside run_bot
            from bot import run_bot
            run_bot()
        except SystemExit as e:
            # 捕获 uvicorn 的退出信号
            print(f"机器人停止运行 (Code: {e})")
            if str(e) == "1":
                print("错误：端口可能被占用。")
                self.root.after(0, lambda: messagebox.showerror("启动失败", "端口被占用，请检查是否有其他机器人实例正在运行。"))
            self.root.after(0, self.reset_ui)
        except Exception as e:
            print(f"Error: {e}")
            self.root.after(0, lambda: messagebox.showerror("运行错误", f"发生错误: {e}"))
            self.root.after(0, self.reset_ui)

    def reset_ui(self):
        self.start_btn.config(state=tk.NORMAL, text="启动机器人")

if __name__ == "__main__":
    # 检查单例
    if is_already_running():
        # 创建一个隐藏的 root 窗口来显示弹窗
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("错误", "程序已经在运行中！")
        sys.exit(0)

    root = tk.Tk()
    app = BotGUI(root)
    root.mainloop()
