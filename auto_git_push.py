import os
import sys
import logging
from datetime import datetime
import subprocess
import time
import platform
import socket
import configparser
import requests
import shutil
import schedule
import threading
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('git_push.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

CONFIG_FILE = 'git_config.ini'

def clear_screen():
    """清除屏幕"""
    os.system('cls' if os.name == 'nt' else 'clear')

def print_menu():
    """打印主菜单"""
    clear_screen()
    print("\n=== Git自动推送工具 ===")
    print("1. 运行自动推送")
    print("2. 配置工作目录")
    print("3. 配置代理设置")
    print("4. 配置Git信息")
    print("5. 安装/更新依赖")
    print("6. 查看当前配置")
    print("7. 配置定时任务")
    print("8. 配置开机自启动")
    print("9. 手动推送")
    print("10. 退出")
    print("===================")

def create_default_config():
    """创建默认配置文件"""
    config = configparser.ConfigParser()
    config['Proxy'] = {
        'enable_proxy': 'false',
        'http_proxy': 'http://127.0.0.1:7890',
        'https_proxy': 'http://127.0.0.1:7890',
        'disable_ssl_verify': 'false'
    }
    config['Git'] = {
        'remote_url': '',
        'branch': 'master',
        'work_dir': os.path.dirname(os.path.abspath(__file__))
    }
    config['Schedule'] = {
        'enable': 'false',
        'interval_minutes': '60',
        'start_time': '09:00',
        'end_time': '18:00'
    }
    config['Startup'] = {
        'enable': 'false'
    }
    
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        config.write(f)
    logger.info(f"已创建默认配置文件: {CONFIG_FILE}")
    return config

def load_config():
    """加载配置文件"""
    config = configparser.ConfigParser()
    
    if not os.path.exists(CONFIG_FILE):
        return create_default_config()
    
    config.read(CONFIG_FILE, encoding='utf-8')
    
    # 确保所有必要的配置项都存在
    if 'Proxy' not in config:
        config['Proxy'] = {}
    if 'Git' not in config:
        config['Git'] = {}
    if 'Schedule' not in config:
        config['Schedule'] = {}
    if 'Startup' not in config:
        config['Startup'] = {}
    
    # 设置默认值
    if 'enable_proxy' not in config['Proxy']:
        config['Proxy']['enable_proxy'] = 'false'
    if 'http_proxy' not in config['Proxy']:
        config['Proxy']['http_proxy'] = 'http://127.0.0.1:7890'
    if 'https_proxy' not in config['Proxy']:
        config['Proxy']['https_proxy'] = 'http://127.0.0.1:7890'
    if 'disable_ssl_verify' not in config['Proxy']:
        config['Proxy']['disable_ssl_verify'] = 'false'
    
    if 'remote_url' not in config['Git']:
        config['Git']['remote_url'] = ''
    if 'branch' not in config['Git']:
        config['Git']['branch'] = 'master'
    if 'work_dir' not in config['Git']:
        config['Git']['work_dir'] = os.path.dirname(os.path.abspath(__file__))
    
    if 'enable' not in config['Schedule']:
        config['Schedule']['enable'] = 'false'
    if 'interval_minutes' not in config['Schedule']:
        config['Schedule']['interval_minutes'] = '60'
    if 'start_time' not in config['Schedule']:
        config['Schedule']['start_time'] = '09:00'
    if 'end_time' not in config['Schedule']:
        config['Schedule']['end_time'] = '18:00'
    
    if 'enable' not in config['Startup']:
        config['Startup']['enable'] = 'false'
    
    # 保存更新后的配置
    save_config(config)
    return config

def save_config(config):
    """保存配置文件"""
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        config.write(f)
    logger.info("配置已保存")

def configure_work_dir():
    """配置工作目录"""
    clear_screen()
    print("\n=== 配置工作目录 ===")
    config = load_config()
    current_dir = config['Git']['work_dir']
    print(f"当前工作目录: {current_dir}")
    
    new_dir = input("\n请输入新的工作目录路径（直接回车保持不变）: ").strip()
    if new_dir:
        if os.path.exists(new_dir):
            config['Git']['work_dir'] = new_dir
            save_config(config)
            print("工作目录已更新！")
            
            # 检查并初始化Git仓库
            if not os.path.exists(os.path.join(new_dir, '.git')):
                print("\n正在初始化Git仓库...")
                output, error, code = run_command('git init', new_dir)
                if code == 0:
                    print("Git仓库初始化成功！")
                    
                    # 如果配置文件中有远程仓库URL，自动添加
                    if config['Git']['remote_url']:
                        print("正在配置远程仓库...")
                        add_remote(new_dir, config['Git']['remote_url'])
                else:
                    print(f"Git仓库初始化失败: {error}")
            else:
                print("\n目录已经是Git仓库")
                
                # 检查远程仓库配置
                remote_output, _, remote_code = run_command('git remote get-url origin', new_dir)
                
                if remote_code != 0 and config['Git']['remote_url']:
                    # 如果本地没有远程仓库配置但配置文件中有，则添加
                    print("正在配置远程仓库...")
                    add_remote(new_dir, config['Git']['remote_url'])
                elif remote_code == 0 and not config['Git']['remote_url']:
                    # 如果本地有远程仓库配置但配置文件中没有，则更新配置文件
                    config['Git']['remote_url'] = remote_output.strip()
                    save_config(config)
                    print(f"已从本地仓库更新远程URL: {remote_output.strip()}")
        else:
            print("错误：目录不存在！")
            
            # 询问是否创建目录
            if input("\n是否创建该目录？(y/n): ").lower().strip() == 'y':
                try:
                    os.makedirs(new_dir)
                    config['Git']['work_dir'] = new_dir
                    save_config(config)
                    print("目录已创建！")
                    
                    # 初始化Git仓库
                    print("\n正在初始化Git仓库...")
                    output, error, code = run_command('git init', new_dir)
                    if code == 0:
                        print("Git仓库初始化成功！")
                        
                        # 如果配置文件中有远程仓库URL，自动添加
                        if config['Git']['remote_url']:
                            print("正在配置远程仓库...")
                            add_remote(new_dir, config['Git']['remote_url'])
                    else:
                        print(f"Git仓库初始化失败: {error}")
                except Exception as e:
                    print(f"创建目录失败: {str(e)}")
    
    input("\n按回车键返回主菜单...")

def configure_proxy():
    """配置代理设置"""
    clear_screen()
    print("\n=== 配置代理设置 ===")
    config = load_config()
    
    print(f"当前代理状态: {'启用' if config.getboolean('Proxy', 'enable_proxy') else '禁用'}")
    print(f"SSL验证: {'禁用' if config.getboolean('Proxy', 'disable_ssl_verify') else '启用'}")
    print(f"HTTP代理: {config['Proxy']['http_proxy']}")
    print(f"HTTPS代理: {config['Proxy']['https_proxy']}")
    
    print("\n1. 启用/禁用代理")
    print("2. 修改代理地址")
    print("3. 启用/禁用SSL验证")
    print("4. 返回主菜单")
    
    choice = input("\n请选择操作 [1-4]: ").strip()
    if choice == '1':
        current = config.getboolean('Proxy', 'enable_proxy')
        config['Proxy']['enable_proxy'] = str(not current)
        save_config(config)
        print(f"代理已{'启用' if not current else '禁用'}！")
    elif choice == '2':
        http_proxy = input("请输入HTTP代理地址（如 http://127.0.0.1:7890）: ").strip()
        https_proxy = input("请输入HTTPS代理地址（如 http://127.0.0.1:7890）: ").strip()
        if http_proxy and https_proxy:
            config['Proxy']['http_proxy'] = http_proxy
            config['Proxy']['https_proxy'] = https_proxy
            save_config(config)
            print("代理地址已更新！")
    elif choice == '3':
        current = config.getboolean('Proxy', 'disable_ssl_verify')
        config['Proxy']['disable_ssl_verify'] = str(not current)
        save_config(config)
        print(f"SSL验证已{'禁用' if not current else '启用'}！")
    
    input("\n按回车键返回主菜单...")

def configure_git():
    """配置Git信息"""
    clear_screen()
    print("\n=== 配置Git信息 ===")
    config = load_config()
    
    print(f"当前远程仓库: {config['Git']['remote_url']}")
    print(f"当前分支: {config['Git']['branch']}")
    
    print("\n1. 修改远程仓库URL")
    print("2. 修改分支名")
    print("3. 配置Git用户信息")
    print("4. 返回主菜单")
    
    choice = input("\n请选择操作 [1-4]: ").strip()
    if choice == '1':
        url = input("请输入新的远程仓库URL: ").strip()
        if url:
            config['Git']['remote_url'] = url
            save_config(config)
            print("远程仓库URL已更新！")
    elif choice == '2':
        branch = input("请输入新的分支名: ").strip()
        if branch:
            config['Git']['branch'] = branch
            save_config(config)
            print("分支名已更新！")
    elif choice == '3':
        username = input("请输入Git用户名: ").strip()
        email = input("请输入Git邮箱: ").strip()
        if username and email:
            run_command(f'git config --global user.name "{username}"')
            run_command(f'git config --global user.email "{email}"')
            print("Git用户信息已更新！")
    
    input("\n按回车键返回主菜单...")

def install_dependencies():
    """安装/更新依赖"""
    clear_screen()
    print("\n=== 安装/更新依赖 ===")
    
    try:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'])
        print("依赖安装/更新成功！")
    except subprocess.CalledProcessError as e:
        print(f"依赖安装失败: {str(e)}")
    
    input("\n按回车键返回主菜单...")

def view_config():
    """查看当前配置"""
    clear_screen()
    print("\n=== 当前配置 ===")
    config = load_config()
    
    print("\n[工作目录]")
    print(f"目录: {config['Git']['work_dir']}")
    
    print("\n[代理设置]")
    print(f"代理状态: {'启用' if config.getboolean('Proxy', 'enable_proxy') else '禁用'}")
    print(f"SSL验证: {'禁用' if config.getboolean('Proxy', 'disable_ssl_verify') else '启用'}")
    print(f"HTTP代理: {config['Proxy']['http_proxy']}")
    print(f"HTTPS代理: {config['Proxy']['https_proxy']}")
    
    print("\n[Git配置]")
    print(f"远程仓库: {config['Git']['remote_url']}")
    print(f"分支: {config['Git']['branch']}")
    
    name_output, _, _ = run_command('git config --global user.name')
    email_output, _, _ = run_command('git config --global user.email')
    print(f"Git用户名: {name_output.strip()}")
    print(f"Git邮箱: {email_output.strip()}")
    
    print("\n[定时任务]")
    print(f"状态: {'启用' if config.getboolean('Schedule', 'enable') else '禁用'}")
    print(f"间隔: {config['Schedule']['interval_minutes']}分钟")
    print(f"开始时间: {config['Schedule']['start_time']}")
    print(f"结束时间: {config['Schedule']['end_time']}")
    
    print("\n[开机自启动]")
    print(f"状态: {'启用' if config.getboolean('Startup', 'enable') else '禁用'}")
    
    input("\n按回车键返回主菜单...")

def check_python_version():
    """检查Python版本"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 6):
        logger.error("Python版本必须是3.6或更高")
        return False
    logger.info(f"Python版本检查通过: {sys.version}")
    return True

def check_git_installed():
    """检查Git是否安装"""
    try:
        output, error, code = run_command('git --version')
        if code == 0:
            logger.info(f"Git版本检查通过: {output.strip()}")
            return True
        else:
            logger.error("Git未安装")
            return False
    except Exception:
        logger.error("Git未安装或不在PATH中")
        return False

def check_git_config():
    """检查Git配置"""
    # 检查用户名和邮箱
    name_output, _, name_code = run_command('git config --global user.name')
    email_output, _, email_code = run_command('git config --global user.email')
    
    if name_code != 0 or not name_output.strip():
        logger.error("Git用户名未配置")
        username = input("请输入Git用户名: ").strip()
        run_command(f'git config --global user.name "{username}"')
    
    if email_code != 0 or not email_output.strip():
        logger.error("Git邮箱未配置")
        email = input("请输入Git邮箱: ").strip()
        run_command(f'git config --global user.email "{email}"')
    
    logger.info("Git配置检查完成")
    return True

def check_github_connection():
    """检查GitHub连接"""
    try:
        config = load_config()
        if config.getboolean('Proxy', 'enable_proxy'):
            proxies = {
                'http': config['Proxy']['http_proxy'],
                'https': config['Proxy']['https_proxy']
            }
            verify = not config.getboolean('Proxy', 'disable_ssl_verify')
            response = requests.get('https://api.github.com', proxies=proxies, verify=verify, timeout=5)
        else:
            verify = not config.getboolean('Proxy', 'disable_ssl_verify')
            response = requests.get('https://api.github.com', verify=verify, timeout=5)
        
        if response.status_code == 200:
            logger.info("GitHub连接正常")
            return True
        else:
            logger.error(f"GitHub连接异常: HTTP {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        logger.error(f"无法连接到GitHub: {str(e)}")
        logger.info("建议配置代理或检查网络连接")
        return False

def setup_proxy():
    """设置Git代理"""
    config = load_config()
    if config.getboolean('Proxy', 'enable_proxy'):
        http_proxy = config['Proxy']['http_proxy']
        https_proxy = config['Proxy']['https_proxy']
        
        # 设置Git代理
        run_command(f'git config --global http.proxy {http_proxy}')
        run_command(f'git config --global https.proxy {https_proxy}')
        
        # 设置环境变量代理
        os.environ['HTTP_PROXY'] = http_proxy
        os.environ['HTTPS_PROXY'] = https_proxy
        
        logger.info(f"已设置代理: {http_proxy}")
    else:
        # 清除Git代理设置
        run_command('git config --global --unset http.proxy')
        run_command('git config --global --unset https.proxy')
        
        # 清除环境变量代理
        os.environ.pop('HTTP_PROXY', None)
        os.environ.pop('HTTPS_PROXY', None)
        
        logger.info("已清除代理设置")

def run_command(command, cwd=None):
    """执行命令并返回输出"""
    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True,
            cwd=cwd
        )
        output, error = process.communicate()
        return output.decode('utf-8'), error.decode('utf-8'), process.returncode
    except Exception as e:
        logger.error(f"执行命令时出错: {str(e)}")
        return None, str(e), 1

def check_git_repo(repo_path):
    """检查Git仓库状态"""
    logger.info(f"检查仓库状态: {repo_path}")
    
    if not os.path.exists(os.path.join(repo_path, '.git')):
        logger.error("当前目录不是Git仓库")
        return False
    
    logger.info("Git仓库已存在")
    
    # 获取远程仓库信息
    remote_output, remote_error, remote_code = run_command('git remote -v', repo_path)
    if remote_code == 0 and remote_output:
        logger.info(f"远程仓库信息:\n{remote_output.strip()}")
    else:
        logger.warning("未配置远程仓库")
    
    # 获取当前分支信息
    branch_output, branch_error, branch_code = run_command('git branch --show-current', repo_path)
    if branch_code == 0:
        logger.info(f"当前分支: {branch_output.strip()}")
    
    # 获取最后一次提交信息
    last_commit_output, last_commit_error, last_commit_code = run_command('git log -1 --oneline', repo_path)
    if last_commit_code == 0:
        logger.info(f"最后一次提交: {last_commit_output.strip()}")
    
    return True

def add_remote(repo_path, remote_url=None):
    """添加远程仓库"""
    config = load_config()
    if not remote_url:
        remote_url = config['Git']['remote_url']
    
    if not remote_url:
        remote_url = input("请输入GitHub仓库URL: ").strip()
        config['Git']['remote_url'] = remote_url
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            config.write(f)
    
    if not check_remote_exists(repo_path):
        logger.info("正在添加远程仓库...")
        output, error, code = run_command(f'git remote add origin {remote_url}', repo_path)
        if code == 0:
            logger.info("远程仓库添加成功")
        else:
            logger.error(f"添加远程仓库失败: {error}")
            return False
    return True

def check_git_changes(repo_path):
    """详细检查Git变更"""
    # 检查未暂存的变更
    diff_output, _, _ = run_command('git diff --numstat', repo_path)
    if diff_output.strip():
        logger.info("未暂存的文件变更:")
        for line in diff_output.strip().split('\n'):
            if line.strip():
                additions, deletions, file = line.split('\t')
                logger.info(f"  {file}: +{additions} -{deletions}")

    # 检查已暂存的变更
    staged_output, _, _ = run_command('git diff --cached --numstat', repo_path)
    if staged_output.strip():
        logger.info("已暂存的文件变更:")
        for line in staged_output.strip().split('\n'):
            if line.strip():
                additions, deletions, file = line.split('\t')
                logger.info(f"  {file}: +{additions} -{deletions}")

    # 检查未跟踪的文件
    untracked_output, _, _ = run_command('git ls-files --others --exclude-standard', repo_path)
    if untracked_output.strip():
        logger.info("未跟踪的文件:")
        for file in untracked_output.strip().split('\n'):
            if file.strip():
                logger.info(f"  {file}")

def push_to_github(repo_path, force_push=False):
    """推送更改到GitHub"""
    config = load_config()
    branch = config['Git']['branch']
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # 检查是否有更改
    logger.info("检查仓库状态...")
    
    # 获取详细的变更信息
    check_git_changes(repo_path)
    
    # 使用porcelain格式获取状态
    status_output, status_error, status_code = run_command('git status --porcelain', repo_path)
    if status_output.strip():
        logger.info("Git状态:")
        for line in status_output.strip().split('\n'):
            status = line[:2]
            file = line[3:]
            status_desc = {
                'M ': '已修改',
                ' M': '已修改但未暂存',
                'A ': '新增到暂存区',
                ' A': '新文件未暂存',
                'D ': '已删除',
                ' D': '已删除但未暂存',
                'R ': '已重命名',
                'C ': '已复制',
                'U ': '更新但未合并',
                '??': '未跟踪'
            }.get(status, '未知状态')
            logger.info(f"  {status_desc}: {file}")
    else:
        logger.info("没有发现新的更改")
    
    if not status_output.strip() and not force_push:
        logger.info("没有需要提交的更改")
        return True

    if not force_push:
        # 添加所有更改
        logger.info("正在添加更改...")
        add_output, add_error, add_code = run_command('git add .', repo_path)
        if add_code != 0:
            logger.error(f"添加更改失败: {add_error}")
            return False
        else:
            # 显示已暂存的更改
            staged_output, _, _ = run_command('git diff --cached --stat', repo_path)
            if staged_output.strip():
                logger.info(f"已暂存以下更改:\n{staged_output.strip()}")

        # 提交更改
        commit_message = f"Auto commit at {timestamp}"
        logger.info(f"正在提交更改: {commit_message}")
        commit_output, commit_error, commit_code = run_command(f'git commit -m "{commit_message}"', repo_path)
        if commit_code != 0:
            logger.error(f"提交更改失败: {commit_error}")
            return False
        else:
            logger.info(f"提交成功: {commit_output.strip()}")

    # 获取远程仓库URL
    remote_url_output, _, remote_url_code = run_command('git remote get-url origin', repo_path)
    if remote_url_code == 0:
        logger.info(f"推送到远程仓库: {remote_url_output.strip()}")
    
    # 获取本地和远程的差异
    ahead_behind, _, _ = run_command(f'git rev-list --left-right --count origin/{branch}...HEAD', repo_path)
    if ahead_behind and len(ahead_behind.split()) == 2:
        behind, ahead = ahead_behind.split()
        if int(ahead) > 0:
            logger.info(f"本地领先远程 {ahead} 个提交")
        if int(behind) > 0:
            logger.info(f"本地落后远程 {behind} 个提交")
    
    # 推送到远程仓库
    logger.info(f"正在推送到远程仓库 (分支: {branch})")
    push_cmd = 'git push origin'
    if config.getboolean('Proxy', 'disable_ssl_verify'):
        push_cmd = 'git -c http.sslVerify=false push origin'
    if force_push:
        push_cmd += f' {branch} -f'
        logger.info("使用强制推送模式")
    else:
        push_cmd += f' {branch}'
    
    push_output, push_error, push_code = run_command(push_cmd, repo_path)
    if push_code != 0:
        logger.error(f"推送失败: {push_error}")
        return False
    else:
        if push_output:
            logger.info(f"推送输出:\n{push_output.strip()}")
        logger.info("成功推送到GitHub")
    return True

def configure_schedule():
    """配置定时任务"""
    clear_screen()
    print("\n=== 配置定时任务 ===")
    config = load_config()
    
    print(f"当前状态: {'启用' if config.getboolean('Schedule', 'enable') else '禁用'}")
    print(f"运行间隔: {config['Schedule']['interval_minutes']}分钟")
    print(f"开始时间: {config['Schedule']['start_time']}")
    print(f"结束时间: {config['Schedule']['end_time']}")
    
    print("\n1. 启用/禁用定时任务")
    print("2. 修改运行间隔")
    print("3. 修改运行时间段")
    print("4. 返回主菜单")
    
    choice = input("\n请选择操作 [1-4]: ").strip()
    if choice == '1':
        current = config.getboolean('Schedule', 'enable')
        config['Schedule']['enable'] = str(not current)
        save_config(config)
        print(f"定时任务已{'启用' if not current else '禁用'}！")
    elif choice == '2':
        interval = input("请输入运行间隔（分钟）: ").strip()
        if interval.isdigit() and int(interval) > 0:
            config['Schedule']['interval_minutes'] = interval
            save_config(config)
            print("运行间隔已更新！")
        else:
            print("无效的时间间隔！")
    elif choice == '3':
        start_time = input("请输入开始时间（格式：HH:MM）: ").strip()
        end_time = input("请输入结束时间（格式：HH:MM）: ").strip()
        try:
            datetime.strptime(start_time, '%H:%M')
            datetime.strptime(end_time, '%H:%M')
            config['Schedule']['start_time'] = start_time
            config['Schedule']['end_time'] = end_time
            save_config(config)
            print("运行时间段已更新！")
        except ValueError:
            print("无效的时间格式！")
    
    input("\n按回车键返回主菜单...")

def configure_startup():
    """配置开机自启动"""
    clear_screen()
    print("\n=== 配置开机自启动 ===")
    config = load_config()
    
    print(f"当前状态: {'启用' if config.getboolean('Startup', 'enable') else '禁用'}")
    
    print("\n1. 启用/禁用开机自启动")
    print("2. 返回主菜单")
    
    choice = input("\n请选择操作 [1-2]: ").strip()
    if choice == '1':
        current = config.getboolean('Startup', 'enable')
        new_state = not current
        
        if new_state:
            # 创建开机启动脚本
            startup_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'startup.bat')
            with open(startup_script, 'w') as f:
                f.write(f'@echo off\n')
                f.write(f'cd /d "{os.path.dirname(os.path.abspath(__file__))}\"\n')
                f.write(f'pythonw "{os.path.abspath(__file__)}" --background\n')
            
            # 创建计划任务
            cmd = f'schtasks /create /tn "GitAutoPush" /tr "{startup_script}" /sc onstart /ru "%USERNAME%" /f'
            output, error, code = run_command(cmd)
            
            if code == 0:
                config['Startup']['enable'] = 'true'
                save_config(config)
                print("开机自启动已启用！")
            else:
                print(f"启用开机自启动失败: {error}")
        else:
            # 删除计划任务
            cmd = 'schtasks /delete /tn "GitAutoPush" /f'
            output, error, code = run_command(cmd)
            
            if code == 0:
                config['Startup']['enable'] = 'false'
                save_config(config)
                print("开机自启动已禁用！")
            else:
                print(f"禁用开机自启动失败: {error}")
    
    input("\n按回车键返回主菜单...")

def run_schedule():
    """运行定时任务"""
    config = load_config()
    if not config.getboolean('Schedule', 'enable'):
        return
    
    current_time = datetime.now().strftime('%H:%M')
    start_time = config['Schedule']['start_time']
    end_time = config['Schedule']['end_time']
    
    if start_time <= current_time <= end_time:
        repo_path = config['Git']['work_dir']
        if os.path.exists(repo_path):
            if check_git_repo(repo_path):
                push_to_github(repo_path)

def schedule_thread():
    """定时任务线程"""
    while True:
        schedule.run_pending()
        time.sleep(60)

def manual_push():
    """手动推送"""
    clear_screen()
    print("\n=== 手动推送 ===")
    config = load_config()
    repo_path = config['Git']['work_dir']
    
    if not os.path.exists(repo_path):
        print(f"错误：工作目录不存在: {repo_path}")
        input("\n按回车键返回主菜单...")
        return
    
    if not os.path.exists(os.path.join(repo_path, '.git')):
        print("错误：当前目录不是Git仓库")
        input("\n按回车键返回主菜单...")
        return
    
    print(f"当前工作目录: {repo_path}")
    print(f"当前分支: {config['Git']['branch']}")
    print("\n1. 正常推送（先add和commit）")
    print("2. 强制推送（直接push -f）")
    print("3. 返回主菜单")
    
    choice = input("\n请选择操作 [1-3]: ").strip()
    if choice == '1':
        push_to_github(repo_path, force_push=False)
    elif choice == '2':
        confirm = input("\n警告：强制推送可能会覆盖远程仓库的更改，是否继续？(y/n): ").lower().strip()
        if confirm == 'y':
            push_to_github(repo_path, force_push=True)
    
    input("\n按回车键返回主菜单...")

def main():
    # 处理命令行参数
    if len(sys.argv) > 1 and sys.argv[1] == '--background':
        # 后台运行模式
        config = load_config()
        if config.getboolean('Schedule', 'enable'):
            interval = int(config['Schedule']['interval_minutes'])
            schedule.every(interval).minutes.do(run_schedule)
            schedule_thread()
        return

    while True:
        print_menu()
        choice = input("\n请选择操作 [1-10]: ").strip()
        
        if choice == '1':
            # 运行自动推送
            config = load_config()
            repo_path = config['Git']['work_dir']
            
            if not os.path.exists(repo_path):
                logger.error(f"工作目录不存在: {repo_path}")
                input("\n按回车键返回主菜单...")
                continue
            
            # 环境检查
            if not all([
                check_python_version(),
                check_git_installed(),
                check_git_config()
            ]):
                logger.error("环境检查未通过，请解决上述问题后重试")
                input("\n按回车键返回主菜单...")
                continue

            # 设置代理
            setup_proxy()

            # 检查GitHub连接
            if not check_github_connection():
                logger.error("无法连接到GitHub，请检查网络或代理设置")
                input("\n按回车键返回主菜单...")
                continue

            # 检查并初始化git仓库
            if not check_git_repo(repo_path):
                input("\n按回车键返回主菜单...")
                continue

            # 推送到GitHub
            push_to_github(repo_path)
            input("\n按回车键返回主菜单...")
            
        elif choice == '2':
            configure_work_dir()
        elif choice == '3':
            configure_proxy()
        elif choice == '4':
            configure_git()
        elif choice == '5':
            install_dependencies()
        elif choice == '6':
            view_config()
        elif choice == '7':
            configure_schedule()
        elif choice == '8':
            configure_startup()
        elif choice == '9':
            manual_push()
        elif choice == '10':
            print("\n感谢使用！再见！")
            break
        else:
            print("\n无效的选择，请重试！")
            time.sleep(1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n程序已被用户中断。再见！")
    except Exception as e:
        logger.error(f"发生错误: {str(e)}")
        print("\n程序发生错误，请查看日志文件了解详情。")
        input("按回车键退出...")
