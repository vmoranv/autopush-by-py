# Git自动推送工具

这是一个自动将本地Git仓库推送到GitHub的工具，支持开机自启动和定时推送功能。

## 功能特点

- 自动检查并初始化Git仓库
- 自动检查环境配置（Python版本、Git安装、Git配置等）
- 支持配置文件管理
- 支持HTTP代理（解决中国境内访问GitHub的问题）
- 使用时间戳作为提交信息
- 详细的日志记录
- 支持开机自启动

## 安装要求

- Python 3.6+
- Git
- requests库 (`pip install -r requirements.txt`)

## 使用方法

1. 安装依赖：
```bash
pip install -r requirements.txt
```

2. 配置文件说明（git_config.ini）：
```ini
[Proxy]
enable_proxy = false
http_proxy = http://127.0.0.1:7890
https_proxy = http://127.0.0.1:7890

[Git]
remote_url = 
branch = master
```

3. 运行脚本：
```bash
python auto_git_push.py
```

4. 设置开机自启动：
- 以管理员身份运行 `setup_startup.bat`

## 代理设置

如果你在中国境内访问GitHub遇到问题，可以：

1. 编辑 `git_config.ini` 文件
2. 将 `enable_proxy` 设置为 `true`
3. 设置正确的代理地址（默认使用 http://127.0.0.1:7890）

## 日志

所有操作日志都会记录在 `git_push.log` 文件中。

## 注意事项

1. 首次运行时会自动创建配置文件
2. 如果未配置Git用户名和邮箱，程序会提示输入
3. 确保有正确的GitHub仓库访问权限
4. 如果使用SSH连接GitHub，确保已配置好SSH密钥
