import tkinter as tk
from tkinter import messagebox
import sys
import os
import threading

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
        
        # Port Config
        self.port_frame = tk.Frame(root)
        self.port_frame.pack(pady=20)
        
        tk.Label(self.port_frame, text="运行端口:").pack(side=tk.LEFT)
        self.port_entry = tk.Entry(self.port_frame)
        self.port_entry.pack(side=tk.LEFT, padx=10)
        
        # Load current port
        self.current_env = self.load_env()
        self.port_entry.insert(0, self.current_env.get("PORT", "8080"))
        
        # Start Button
        self.start_btn = tk.Button(root, text="保存配置并启动", command=self.start_bot, height=2, width=20)
        self.start_btn.pack(pady=5)

        # Restart Button
        self.restart_btn = tk.Button(root, text="重启程序", command=self.restart_app, height=2, width=20)
        self.restart_btn.pack(pady=5)

        #stop Button
        # self.stop_btn = tk.Button(root, text="停止程序", command=self.stop_app, height=2, width=20)
        # self.stop_btn.pack(pady=5)
        
        # Log area
        self.log_text = tk.Text(root, height=15)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Redirect stdout
        sys.stdout = TextRedirector(self.log_text)
        sys.stderr = TextRedirector(self.log_text)

    def load_env(self):
        env = {}
        if os.path.exists(".env"):
            with open(".env", "r", encoding="utf-8") as f:
                for line in f:
                    if "=" in line:
                        parts = line.strip().split("=", 1)
                        if len(parts) == 2:
                            env[parts[0].strip()] = parts[1].strip()
        return env

    def save_env(self):
        port = self.port_entry.get()
        # Update env dict
        self.current_env["PORT"] = port
        
        lines = []
        if os.path.exists(".env"):
            with open(".env", "r", encoding="utf-8") as f:
                lines = f.readlines()
        
        new_lines = []
        port_found = False
        for line in lines:
            if line.strip().startswith("PORT="):
                new_lines.append(f"PORT={port}\n")
                port_found = True
            else:
                new_lines.append(line)
        
        if not port_found:
            new_lines.append(f"PORT={port}\n")
            
        with open(".env", "w", encoding="utf-8") as f:
            f.writelines(new_lines)

    def start_bot(self):
        self.save_env()
        self.start_btn.config(state=tk.DISABLED, text="正在运行...")
        
        # Run in thread
        t = threading.Thread(target=self.run_bot_thread, daemon=True)
        t.start()

    def restart_app(self):
        try:
            self.save_env()
            import subprocess
            
            if getattr(sys, 'frozen', False):
                # Frozen mode: sys.executable is the exe
                subprocess.Popen([sys.executable] + sys.argv[1:])
            else:
                # Dev mode: sys.executable is python interpreter
                subprocess.Popen([sys.executable] + sys.argv)
                
            self.root.quit()
            sys.exit()
        except Exception as e:
            messagebox.showerror("重启失败", f"无法重启程序: {e}")

    # def stop_app(self):
    #     if messagebox.askokcancel("停止程序", "确定要停止程序吗？"):
    #         self.root.destroy()

    def run_bot_thread(self):
        try:
            print("正在启动机器人...")
            # Import here to ensure env is loaded by nonebot.init() which happens inside run_bot
            from bot import run_bot
            run_bot()
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = BotGUI(root)
    root.mainloop()
