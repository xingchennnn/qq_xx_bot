@echo off
chcp 65001 >nul
setlocal

cd /d %~dp0

REM ========================================================
REM 配置区域
REM ========================================================

REM 设置虚拟环境目录名称
set "VENV_NAME=.venv"

REM 设置自定义 Python 路径 (可选，如果想使用特定 Python 版本)
REM 如果当前目录下有 python 文件夹，则优先使用
if exist "%~dp0python\python.exe" (
    set "PYTHON_EXE=%~dp0python\python.exe"
) else (
    set "PYTHON_EXE=python"
)

REM 设置国内镜像源（清华源）
set "PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple"

REM ========================================================
REM 脚本逻辑
REM ========================================================

echo [INFO] 正在检查 Python 环境...

REM 检查 Python 是否可用
"%PYTHON_EXE%" --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] 未找到 Python！
    echo 请确保已安装 Python 并添加到环境变量 PATH 中。
    echo 或者将 Python 嵌入式包解压到当前目录的 python 文件夹中。
    pause
    exit /b 1
)

REM 检查虚拟环境是否存在
if not exist "%~dp0%VENV_NAME%" (
    echo [INFO] 未检测到虚拟环境，正在创建...
    "%PYTHON_EXE%" -m venv "%~dp0%VENV_NAME%"
    if %errorlevel% neq 0 (
        echo [ERROR] 创建虚拟环境失败！
        pause
        exit /b 1
    )
    echo [INFO] 虚拟环境创建成功。
) else (
    echo [INFO] 检测到已有虚拟环境。
)

REM 激活虚拟环境
call "%~dp0%VENV_NAME%\Scripts\activate.bat"

REM 检查并安装依赖
if exist "%~dp0requirements.txt" (
    echo [INFO] 正在检查并更新依赖...
    pip install --upgrade pip -i %PIP_INDEX_URL%
    pip install -r "%~dp0requirements.txt" -i %PIP_INDEX_URL%
    if %errorlevel% neq 0 (
        echo [ERROR] 依赖安装失败！
        pause
        exit /b 1
    )
) else (
    echo [WARN] 未找到 requirements.txt，跳过依赖安装。
)

REM 启动机器人
echo.
echo [INFO] 正在启动机器人...
echo [SUCCESS] 请在机器人启动后,在napcat中配置加上  ws://127.0.0.1:8080/onebot/v11/ws
echo ========================================================
python bot.py
echo ========================================================
echo [INFO] 机器人已停止运行。

pause