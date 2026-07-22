# 效贷测试专家 - 安装后注册脚本
# 用途：将已安装的 xiaodai-testing-expert 套件注册为 WorkBuddy 专家
# 使用方法：双击 register_expert.bat，或右键本文件 →"使用 PowerShell 运行"
# 前提：已通过团队市场安装 xiaodai-test-expert 套件

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "  效贷测试专家 - 安装后注册脚本" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

# 1. 定位 WorkBuddy 主目录
$wbHome = Join-Path $env:USERPROFILE ".workbuddy"
if (-not (Test-Path $wbHome)) {
    Write-Host "[X] 未找到 WorkBuddy 目录: $wbHome" -ForegroundColor Red
    Write-Host "请确认 WorkBuddy 已安装并至少打开过一次。" -ForegroundColor Yellow
    Read-Host "按回车键退出"
    exit 1
}
Write-Host "[1/4] WorkBuddy 目录: $wbHome" -ForegroundColor Green

# 2. 获取用户 ID
$userId = $null

# 方式 A：从 sessions.json 获取
$sessionsPath = Join-Path $wbHome "app\sessions.json"
if ((-not $userId) -and (Test-Path $sessionsPath)) {
    try {
        $sessions = Get-Content $sessionsPath -Encoding UTF8 -Raw | ConvertFrom-Json
        if ($sessions.sessions -and $sessions.sessions.Count -gt 0) {
            foreach ($s in $sessions.sessions) {
                if ($s.userId) {
                    $userId = $s.userId
                    break
                }
            }
        }
    } catch {
        Write-Host "[!] sessions.json 解析失败，尝试其他方式..." -ForegroundColor Yellow
    }
}

# 方式 B：从 experts/custom 目录中查找已有用户目录
if (-not $userId) {
    $customBase = Join-Path $wbHome "experts\custom"
    if (Test-Path $customBase) {
        $userDirs = Get-ChildItem $customBase -Directory -ErrorAction SilentlyContinue
        if ($userDirs -and $userDirs.Count -gt 0) {
            $userId = $userDirs[0].Name
        }
    }
}

if (-not $userId) {
    Write-Host "[X] 无法自动获取用户 ID。" -ForegroundColor Red
    Write-Host ""
    Write-Host "请手动执行以下步骤：" -ForegroundColor Yellow
    Write-Host "  1. 在 WorkBuddy 中随便发起一个对话（新建会话）"
    Write-Host "  2. 完全退出 WorkBuddy"
    Write-Host "  3. 重新运行本脚本"
    Read-Host "按回车键退出"
    exit 1
}
Write-Host "[2/4] 用户 ID: $userId" -ForegroundColor Green

# 3. 检查套件是否已安装
$settingsPath = Join-Path $wbHome "settings.json"
$pluginInstalled = $false
if (Test-Path $settingsPath) {
    try {
        $settings = Get-Content $settingsPath -Encoding UTF8 -Raw | ConvertFrom-Json
        if ($settings.enabledPlugins) {
            $pluginKey = "xiaodai-testing-expert@xiaodai-test-expert-marketplace"
            $prop = $settings.enabledPlugins.PSObject.Properties[$pluginKey]
            if ($prop -and $prop.Value -eq $true) {
                $pluginInstalled = $true
            }
        }
    } catch {}
}

if ($pluginInstalled) {
    Write-Host "[3/4] 套件已安装" -ForegroundColor Green
} else {
    Write-Host "[!] 未检测到已安装的 xiaodai-testing-expert 套件。" -ForegroundColor Yellow
    Write-Host "    请先在 WorkBuddy 中安装套件后再运行本脚本。" -ForegroundColor Yellow
    $continue = Read-Host "是否仍然继续注册？(y/n)"
    if ($continue -ne "y" -and $continue -ne "Y") {
        Read-Host "按回车键退出"
        exit 0
    }
    Write-Host "[3/4] 跳过套件检查" -ForegroundColor Green
}

# 4. 写入专家注册表
$customDir = Join-Path $wbHome "experts\custom\$userId"
$expertsJsonPath = Join-Path $customDir "experts.json"
$expertId = "xiaodai-testing-expert"

# 检查是否已注册
$alreadyRegistered = $false
if (Test-Path $expertsJsonPath) {
    try {
        $existing = Get-Content $expertsJsonPath -Encoding UTF8 -Raw | ConvertFrom-Json
        if ($existing -is [string]) {
            $existing = @($existing)
        }
        if ($existing -contains $expertId) {
            $alreadyRegistered = $true
        }
    } catch {}
}

if ($alreadyRegistered) {
    Write-Host "[4/4] 专家已注册，无需重复操作。" -ForegroundColor Green
} else {
    # 创建目录
    if (-not (Test-Path $customDir)) {
        New-Item -ItemType Directory -Path $customDir -Force | Out-Null
    }

    # 构建专家列表
    $expertList = @($expertId)
    if (Test-Path $expertsJsonPath) {
        try {
            $existingList = Get-Content $expertsJsonPath -Encoding UTF8 -Raw | ConvertFrom-Json
            if ($existingList -is [string]) {
                $existingList = @($existingList)
            }
            if ($existingList -and $existingList -notcontains $expertId) {
                $expertList = @($existingList) + @($expertId)
            }
        } catch {}
    }

    # 写入 JSON（UTF-8 无 BOM）
    if ($expertList.Count -eq 1) {
        $jsonContent = "[`n  `"$expertId`"`n]"
    } else {
        $jsonContent = $expertList | ConvertTo-Json -Depth 5
    }
    [System.IO.File]::WriteAllText($expertsJsonPath, $jsonContent, [System.Text.UTF8Encoding]::new($false))

    Write-Host "[4/4] 专家注册成功！" -ForegroundColor Green
}

Write-Host ""
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "  注册完成！" -ForegroundColor Green
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "下一步操作：" -ForegroundColor White
Write-Host "  1. 完全退出 WorkBuddy（托盘图标右键 -> 退出）" -ForegroundColor White
Write-Host "  2. 重新打开 WorkBuddy" -ForegroundColor White
Write-Host "  3. 进入 [专家 技能 链接] -> [专家] -> 右上角 [我的专家]" -ForegroundColor White
Write-Host "  4. 应该能看到 [效贷测试专家]" -ForegroundColor White
Write-Host ""
Read-Host "按回车键退出"
