@echo off
chcp 65001 >nul 2>&1
echo.
echo =========================================
echo   效贷测试专家 - 安装后注册脚本
echo =========================================
echo.
echo 正在启动 PowerShell 脚本...
echo.

powershell.exe -ExecutionPolicy Bypass -File "%~dp0register_expert.ps1"

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [提示] 如果脚本执行失败，请尝试以下方法：
    echo   1. 右键点击 register_expert.ps1
    echo   2. 选择"使用 PowerShell 运行"
)

pause
