import nonebot
from nonebot.adapters.onebot.v11 import Adapter as ONEBOT_V11Adapter
import sys
import os

def run_bot():
    # 初始化 NoneBot
    nonebot.init()

    # 注册适配器
    driver = nonebot.get_driver()
    driver.register_adapter(ONEBOT_V11Adapter)

    # 加载插件
    # 检测是否打包环境
    if getattr(sys, 'frozen', False):
        # 打包环境，通过模块名加载
        # 必须与 build.bat 中的 --hidden-import 对应
        plugins = [
            "src.plugins.auto_bounty",
            "src.plugins.auto_matic",
            "src.plugins.auto_sell",
            "src.plugins.merge_task_bounty",
            "src.plugins.qq_handler",
            "src.plugins.sect_task"
        ]
        for plugin in plugins:
            try:
                nonebot.load_plugin(plugin)
            except Exception as e:
                print(f"Failed to load plugin {plugin}: {e}")
    else:
        # 开发环境路径
        plugin_dir = "src/plugins"
        # 这里加载 src/plugins 目录下的插件
        nonebot.load_plugins(plugin_dir)

    nonebot.run()

if __name__ == "__main__":
    run_bot()
