@echo off
echo 正在创建开机启动任务...

:: 创建计划任务，在开机时运行脚本
schtasks /create /tn "GitAutoPush" /tr "python %~dp0auto_git_push.py" /sc onstart /ru "%USERNAME%" /f

echo 开机启动任务已创建完成！
pause
