@echo off
chcp 65001 >nul 2>&1

echo.
echo =========================================
echo   效贷测试专家 - 安装后注册脚本
echo =========================================
echo.

set "PS1_FILE=%~dp0register_expert.ps1"

:: 优先尝试 PowerShell 7 (pwsh.exe)，如果失败再尝试 Windows PowerShell (powershell.exe)
set "PWSH_FOUND=0"

where pwsh.exe >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [信息] 使用 PowerShell 7 (pwsh.exe) 运行...
    echo.
    pwsh.exe -ExecutionPolicy Bypass -File "%PS1_FILE%"
    set "PWSH_FOUND=1"
    goto :DONE
)

where powershell.exe >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [信息] 使用 Windows PowerShell (powershell.exe) 运行...
    echo.
    powershell.exe -ExecutionPolicy Bypass -File "%PS1_FILE%"
    set "PWSH_FOUND=1"
    goto :DONE
)

:: 如果都没找到
if "%PWSH_FOUND%"=="0" (
    echo.
    echo [X] 错误：当前系统未找到 PowerShell。
    echo.
    echo 请尝试以下方法之一：
    echo   方法 1：右键点击 register_expert.ps1，选择"使用 PowerShell 运行"
    echo   方法 2：安装 PowerShell 7 后重新运行本脚本
    echo   方法 3：手动创建注册文件
    echo.
    echo 手动注册步骤：
    echo   1. 打开文件夹：%%USERPROFILE%%\.workbuddy\experts\custom\
    echo   2. 如果 custom 下没有以你的 userId 命名的文件夹，
    echo      请从 %%USERPROFILE%%\.workbuddy\app\sessions.json 中找到 userId
    echo   3. 在 userId 文件夹下创建 experts.json，内容：
    echo      ["xiaodai-testing-expert"]
    echo   4. 重启 WorkBuddy
    echo.
)

:DONE
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [提示] PowerShell 脚本执行失败，错误码：%ERRORLEVEL%
)

echo.
pause
