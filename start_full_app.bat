@echo off
title LDPC 完整应用启动器
color 0A

echo ==========================================
echo    LDPC 可视化系统 - 完整应用启动器
echo ==========================================
echo.

:: 设置路径
set BACKEND_PATH=%~dp0backend
set FRONTEND_PATH=%~dp0my_ldpc_app

:: 检查目录是否存在
if not exist "%BACKEND_PATH%" (
    echo 错误: 后端目录不存在 %BACKEND_PATH%
    pause
    exit /b 1
)

if not exist "%FRONTEND_PATH%" (
    echo 错误: 前端目录不存在 %FRONTEND_PATH%
    pause
    exit /b 1
)

echo [1/4] 检查Python环境...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo 错误: Python未安装或未添加到PATH
    echo 请先安装Python: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [2/4] 检查Flutter环境...
flutter --version >nul 2>&1
if %errorlevel% neq 0 (
    echo 错误: Flutter未安装或未添加到PATH
    echo 请先安装Flutter: https://flutter.dev/docs/get-started/install
    pause
    exit /b 1
)

echo [3/4] 启动后端服务器...
cd /d "%BACKEND_PATH%"
start "LDPC Backend" cmd /k "echo 正在启动后端服务器... && python main.py"

echo [4/4] 等待后端启动（5秒）...
timeout /t 5 /nobreak >nul

echo [5/5] 启动前端应用...
cd /d "%FRONTEND_PATH%"
start "LDPC Frontend" cmd /k "echo 正在启动前端应用... && flutter run -d windows"

echo.
echo ==========================================
echo    应用启动完成！
echo ==========================================
echo.
echo 后端服务器: http://localhost:8000
echo 前端应用: 将在新窗口中打开
echo.
echo 使用说明:
echo 1. 创建LDPC图（添加变量节点和校验节点）
echo 2. 生成LDPC码
echo 3. 配置解码参数
echo 4. 执行解码操作
echo.
echo 按任意键关闭此窗口...
pause >nul 