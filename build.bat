@echo off
chcp 65001 >nul
setlocal

echo 正在激活虚拟环境...
call .venv\Scripts\activate
if errorlevel 1 (
    echo 激活虚拟环境失败，请检查 .venv 是否存在。
    pause
    exit /b 1
)

REM 设置国内镜像源（清华源）
set "PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple"

echo 正在检查 PyInstaller...
pip show pyinstaller >nul 2>&1
if %errorlevel% neq 0 (
    echo 未检测到 PyInstaller，正在安装...
    pip install pyinstaller -i https://pypi.tuna.tsinghua.edu.cn/simple
    if errorlevel 1 (
        echo PyInstaller 安装失败。
        pause
        exit /b 1
    )
) else (
    echo PyInstaller 已安装，跳过安装。
)

if exist "dist\qqBot.exe" (
    echo 正在检查旧版 qqBot.exe 是否被占用...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "$exe = (Resolve-Path 'dist\qqBot.exe').Path; $locked = Get-Process | Where-Object { $_.Path -eq $exe }; if ($locked) { $locked | ForEach-Object { Write-Host ('占用进程: {0} PID={1}' -f $_.ProcessName, $_.Id) }; exit 1 }"
    if errorlevel 1 (
        echo 请先关闭正在运行的 dist\qqBot.exe 后再重新打包。
        pause
        exit /b 1
    )

    del /f /q "dist\qqBot.exe"
    if errorlevel 1 (
        echo 删除旧版 dist\qqBot.exe 失败，请检查文件权限。
        pause
        exit /b 1
    )
)

echo 正在打包...
pyinstaller --onefile --noconsole --name qqBot ^
    --add-data "src;src" ^
    --add-data ".env;." ^
    --hidden-import src.plugins.auto_bounty ^
    --hidden-import src.plugins.auto_mining ^
    --hidden-import src.plugins.auto_matic ^
    --hidden-import src.plugins.auto_sell ^
    --hidden-import src.plugins.merge_task_bounty ^
    --hidden-import src.plugins.qq_handler ^
    --hidden-import src.plugins.sect_task ^
    --hidden-import src.plugins.system ^
    --hidden-import src.plugins.linglu ^
    --hidden-import src.plugins.common ^
    --hidden-import nonebot.drivers.fastapi ^
    --hidden-import uvicorn ^
    gui.py
if errorlevel 1 (
    echo 打包失败，请查看上方 PyInstaller 错误信息。
    pause
    exit /b 1
)

echo 打包完成！
echo dist\qqBot.exe
echo .env 文件已集成到 exe 中，如需修改配置，可在 exe 同级目录下创建 .env 文件覆盖默认配置。
pause
