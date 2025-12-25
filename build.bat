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
    --add-data ".env;." ^
    --hidden-import src.plugins.auto_bounty ^
    --hidden-import src.plugins.auto_matic ^
    --hidden-import src.plugins.auto_sell ^
    --hidden-import src.plugins.merge_task_bounty ^
    --hidden-import src.plugins.qq_handler ^
    --hidden-import src.plugins.sect_task ^
    --hidden-import src.plugins.system ^
    --hidden-import nonebot.drivers.fastapi ^
    --hidden-import uvicorn ^
    gui.py

echo 打包完成！
echo 可执行文件位于 dist\qqBot.exe
echo .env 文件已集成到 exe 中，如需修改配置，可在 exe 同级目录下创建 .env 文件覆盖默认配置。
pause