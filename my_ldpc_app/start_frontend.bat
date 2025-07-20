@echo off
echo ========================================
echo    启动 LDPC 前端应用 (Flutter)
echo ========================================
echo.

:: 检查是否在正确的目录
if not exist "pubspec.yaml" (
    echo 错误: 请在Flutter项目根目录中运行此脚本
    echo 当前目录: %cd%
    pause
    exit /b 1
)

:: 检查Flutter是否已安装
flutter --version >nul 2>&1
if %errorlevel% neq 0 (
    echo 错误: Flutter未安装或未添加到PATH
    echo 请先安装Flutter: https://flutter.dev/docs/get-started/install
    pause
    exit /b 1
)

echo 正在检查Flutter项目...
flutter doctor --no-version-check

echo.
echo 正在获取依赖项...
flutter pub get

echo.
echo 正在启动Flutter应用...
echo 注意: 请确保后端服务器正在运行 (http://localhost:5000)
echo.

:: 启动Flutter应用
flutter run -d windows

echo.
echo 应用已退出。
pause 