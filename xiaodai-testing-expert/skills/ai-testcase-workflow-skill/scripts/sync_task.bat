@echo off
REM ============================================================
REM 效贷测试专家 - 时间记录同步到 MySQL
REM 依赖：Python 3.6+（pymysql 已打包进 scripts 目录，无需 pip install）
REM 定时：每天 12:00 / 18:00 各一次
REM
REM 首次注册计划任务（以管理员身份运行 CMD，执行以下两条）：
REM   schtasks /create /tn "效贷时间同步-午" /tr "%~dp0sync_task.bat" /sc daily /st 12:00 /f
REM   schtasks /create /tn "效贷时间同步-晚" /tr "%~dp0sync_task.bat" /sc daily /st 18:00 /f
REM
REM 查看：   schtasks /query /tn "效贷时间同步-午"
REM 删除：   schtasks /delete /tn "效贷时间同步-午" /f & schtasks /delete /tn "效贷时间同步-晚" /f
REM ============================================================

REM 切换到脚本目录（确保加载同目录打包的 pymysql）
cd /d "%~dp0"

REM 运行同步，日志追加到本地
python sync_to_mysql.py --biz-line 效贷 >> "%~dp0sync_log.txt" 2>&1

exit /b %ERRORLEVEL%
