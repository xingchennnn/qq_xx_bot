@echo off
chcp 65001 >nul
setlocal

echo 正在激活虚拟环境...
call .venv\Scripts\activate

REM 设置国内镜像源（清华源）
set "PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple"

echo 正在安装 PyInstaller...
pip install pyinstaller -i https://pypi.tuna.tsinghua.edu.cn/simple

echo 正在打包...
pyinstaller --onefile --noconsole --name qqBot ^
    --add-data "src;src" ^
    --hidden-import src.plugins.auto_bounty ^
    --hidden-import src.plugins.auto_matic ^
    --hidden-import src.plugins.auto_sell ^
    --hidden-import src.plugins.merge_task_bounty ^
    --hidden-import src.plugins.qq_handler ^
    --hidden-import src.plugins.sect_task ^
    --hidden-import nonebot.drivers.fastapi ^
    --hidden-import uvicorn ^
    gui.py

echo 打包完成！
echo 可执行文件位于 dist\qqBot.exe
echo 请确保将 .env 文件复制到 dist 目录下与 exe 同级。
pause