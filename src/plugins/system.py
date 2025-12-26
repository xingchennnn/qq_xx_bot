from nonebot import on_command
from nonebot.rule import to_me
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent, MessageSegment
from nonebot.exception import FinishedException
import subprocess
import sys
import os
import httpx

VERSION = "1.0.5"

help_cmd = on_command("help", aliases={"帮助", "菜单"}, rule=to_me(), priority=1)
update_cmd = on_command("update", aliases={"更新", "升级"}, rule=to_me(), priority=1)

@help_cmd.handle()
async def handle_help(bot: Bot, event: GroupMessageEvent):
    msg = (
        f"当前版本：{VERSION}\n"
        "当前可用指令：\n"
        "1. 自动任务 (推荐) - 自动执行  修仙签到->领丹药->宗门任务->悬赏令\n"
        "2. 自动宗门任务 - 单独执行宗门任务\n"
        "3. 自动悬赏 - 单独执行悬赏令\n"
        "4. 自动售卖 [价格偏移] - 自动上架药材\n"
        "5. 每日流程 - 签到、领丹药等\n"
        "6. 灵露收集 - 自动收集灵露直到收益归零\n"
        "7. 更新 - 检查并更新机器人\n"
        "\n"
        "注意：所有指令需 @机器人 使用"
    )
    await help_cmd.send(msg)


@update_cmd.handle()
async def handle_update(bot: Bot, event: GroupMessageEvent):
    await update_cmd.send(f"正在检查更新... 当前版本: {VERSION}")
    try:
        # 检查是否是打包环境
        if getattr(sys, 'frozen', False):
            await update_cmd.send("正在检查 Gitee 最新版本...")
            try:
                async with httpx.AsyncClient() as client:
                    # 获取最新版本信息
                    resp = await client.get("https://gitee.com/api/v5/repos/kuirao/qq_xx_bot/releases/latest")
                    resp.raise_for_status()
                    data = resp.json()
                    latest_tag = data["tag_name"]
                    latest_version = latest_tag.replace("qq_xx_bot_", "")
                    
                    if latest_version == VERSION:
                        await update_cmd.finish("当前已是最新版本。")
                        return
                        
                    # 获取文件大小信息
                    # assets = data.get("assets", [])
                    # target_asset = next((a for a in assets if a["name"] == "qqBot.exe"), None)
                    # expected_size = target_asset["size"] if target_asset else 0
                    
                    await update_cmd.send(f"发现新版本: {latest_version}，正在下载...")
                    
                    # 下载新版本 (流式下载)
                    download_url = f"https://gitee.com/kuirao/qq_xx_bot/releases/download/{latest_tag}/qqBot.exe"
                    new_exe = "qqBot_new.exe"
                    
                    try:
                        async with client.stream("GET", download_url, follow_redirects=True) as response:
                            response.raise_for_status()
                            with open(new_exe, "wb") as f:
                                async for chunk in response.aiter_bytes():
                                    f.write(chunk)
                    except Exception as e:
                        await update_cmd.finish(f"下载出错: {e}")
                        return
                        
                    # 验证文件大小
                    # if expected_size > 0:
                    #     actual_size = os.path.getsize(new_exe)
                    #     if actual_size != expected_size:
                    #         await update_cmd.finish(f"更新失败：下载文件不完整 (预期 {expected_size} 字节, 实际 {actual_size} 字节)")
                    #         return
                        
                    # 创建更新脚本
                    current_exe = sys.executable
                    exe_name = os.path.basename(current_exe)
                    
                    bat_script = f"""@echo off
setlocal
cd /d "%~dp0"
set "_MEIPASS2="
set "PYTHONPATH="
set "PYTHONHOME="

timeout /t 2 /nobreak >nul

:del_loop
if exist "{exe_name}" (
    del "{exe_name}" >nul 2>&1
    if exist "{exe_name}" (
        timeout /t 1 /nobreak >nul
        goto del_loop
    )
)

ren "{new_exe}" "{exe_name}"
timeout /t 1 /nobreak >nul

start "" explorer "{exe_name}"
endlocal
del "%~f0"
"""
                    with open("update.bat", "w", encoding="gbk") as f:
                        f.write(bat_script)
                        
                    await update_cmd.send("下载完成，正在重启进行更新...")
                    
                    # 启动脚本并退出
                    # 使用 os.startfile 启动 bat，bat 中使用 explorer 启动 exe，彻底隔离环境
                    os.startfile("update.bat")
                    os._exit(0)
            
            except FinishedException:
                raise
            except Exception as e:
                print(f"自动更新失败: {e}")
                await update_cmd.finish(f"自动更新失败：{e}\n请尝试手动下载：https://gitee.com/kuirao/qq_xx_bot/releases")
            return

        # 执行 git pull
        process = subprocess.run(["git", "pull"], capture_output=True, text=True, encoding="utf-8")
        
        if process.returncode != 0:
            await update_cmd.finish(f"更新失败：\n{process.stderr}")
            return

        if "Already up to date" in process.stdout or "已经是最新" in process.stdout:
            await update_cmd.finish("当前已是最新版本。")
        else:
            await update_cmd.send(f"更新成功！\n{process.stdout}\n正在重启机器人...")
            
            # 重启机器人
            python = sys.executable
            os.execl(python, python, *sys.argv)
            
    except FinishedException:
        raise
    except Exception as e:
        await update_cmd.finish(f"更新出错：{str(e)}")
