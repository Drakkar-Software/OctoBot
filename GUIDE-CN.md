# OctoBot 源码安装与使用指南

本指南介绍如何在 **Linux、macOS、WSL 2 和 Windows** 上使用 **uv** 从源码安装、运行和更新 OctoBot。

> 本指南只介绍 **uv + Python 3.13 源码安装**。默认已完成 WSL 2 初始化，并已安装 uv，`uv` 应可在终端中直接调用。本文不再说明 WSL 和 uv 的安装过程；Git 与各平台编译工具的准备见对应平台章节。
>
> Python 解释器、虚拟环境、项目依赖和本地 `packages/*` 包均由 uv 管理，不需要手动设置 `PYTHONPATH`。

平台与终端对应关系：

| 平台 | 推荐终端 | 本文命令章节 |
|---|---|---|
| Linux | Bash 或 Zsh | [第 2 章](#2-linuxmacos-与-wsl-2) |
| macOS | Terminal 或 iTerm2 | [第 2 章](#2-linuxmacos-与-wsl-2) |
| WSL 2 | Ubuntu 终端 | [第 2 章](#2-linuxmacos-与-wsl-2) |
| Windows | PowerShell | [第 3 章](#3-windows-原生安装) |

相关文档：

- [OctoBot 中文 README](README-CN.md)
- [uv 项目管理文档](https://docs.astral.sh/uv/concepts/projects/)
- [Git 安装文档](https://git-scm.com/downloads)
- [OctoBot Beta 节点模式入门](docs/content/guides/octobot-beta-getting-started.md)

## 1. 通用准备

### 1.1 系统要求

建议使用 64 位系统和稳定的网络连接：

- Python **3.13 或更高版本**（由 uv 自动安装和管理）
- Git
- 至少 2 GB 可用内存；运行多个实例或回测时建议 4 GB 以上
- 至少 5 GB 可用磁盘空间，用于 Python、依赖、插件和回测数据

依赖安装和回测会持续读写项目目录。请把源码放在本地磁盘，不要放在网络共享目录、同步盘或受保护的系统目录中。

### 1.2 默认端口

| 地址 | 用途 |
|---|---|
| `http://localhost:8000` | 默认节点模式 API 与本地节点界面 |
| `http://localhost:5001` | `--standalone` 经典交易 Web 界面 |
| `http://localhost:5001` 至 `5010` | 节点启动的手动 OctoBot 子实例 |

### 1.3 常用 uv 命令

本指南使用的核心命令如下：

```text
uv python install 3.13
uv sync --locked --python 3.13 --extra full --extra socks --group dev
uv run --locked OctoBot
```

- `uv sync` 根据 `pyproject.toml` 和 `uv.lock` 创建或更新 `.venv`。
- `--locked` 要求安装内容与 `uv.lock` 完全一致。
- `--extra full` 安装插件和完整功能依赖。
- `--extra socks` 安装 SOCKS 代理支持。
- `--group dev` 安装开发、测试和代码检查工具。

## 2. Linux、macOS 与 WSL 2

Linux、macOS 和 WSL 2 使用相同的 Bash/Zsh 命令。以下步骤假定 WSL 2、Linux 发行版、Git、uv 和基础编译工具均已安装并位于 `PATH` 中。

> WSL 项目必须放在 Linux 文件系统中，例如 `~/projects/OctoBot`。不要把项目放在 `/mnt/c`、`/mnt/d` 等 Windows 挂载目录，否则文件监听、依赖安装和回测都会明显变慢。


### 2.1 获取源码

```bash
mkdir -p "$HOME/projects"
cd "$HOME/projects"
git clone https://github.com/Drakkar-Software/OctoBot.git
cd OctoBot
```

如果需要使用开发分支：

```bash
git checkout dev
```

### 2.2 安装 Python 与项目依赖

```bash
./install.sh
uv python install 3.13
uv sync --locked --python 3.13 --extra full --extra socks --group dev
```

uv 会完成以下工作：

- 下载并使用 Python 3.13；
- 在仓库根目录创建 `.venv`；
- 按 `uv.lock` 安装锁定版本的依赖；
- 以可编辑模式安装 OctoBot、`packages/*` 中的全部 Python 包和 `OctoBot` 命令；
- 安装完整功能、SOCKS 代理和开发测试依赖。

不需要手动执行 `python -m venv`、`source .venv/bin/activate` 或设置 `PYTHONPATH`。

如果 `cryptography` 等包要求从源码编译，Ubuntu/WSL 可以安装 Rust 工具链后重试：

```bash
sudo apt install -y rustc cargo
uv sync --locked --python 3.13 --extra full --extra socks --group dev
```

macOS 可先确认命令行工具完整，再使用 rustup 安装 Rust：

```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source "$HOME/.cargo/env"
uv sync --locked --python 3.13 --extra full --extra socks --group dev
```

### 2.3 安装插件并启动

首次运行前安装全部插件：

```bash
cd "$HOME/projects/OctoBot"
uv run --locked OctoBot tentacles --install --all
```

启动默认节点模式：

```bash
uv run --locked OctoBot
```

启动后打开：

```text
http://localhost:8000
```

如果需要经典交易 Web 界面，使用 standalone 模式：

```bash
uv run --locked OctoBot --standalone
```

此时打开：

```text
http://localhost:5001
```

WSL 通常无法直接调用 Windows 浏览器，请手动复制地址。Linux 和 macOS 通常会自动打开默认浏览器；如果没有自动打开，手动访问上述地址即可。

### 2.4 后台运行

Linux、macOS 和 WSL 可以使用 `tmux` 保持进程运行：

```bash
tmux new -s octobot
cd "$HOME/projects/OctoBot"
uv run --locked OctoBot
```

按 `Ctrl+B`，再按 `D` 退出会话。重新连接：

```bash
tmux attach -t octobot
```

Debian/Ubuntu/WSL 安装 tmux：

```bash
sudo apt install -y tmux
```

macOS 可以使用 Homebrew 安装：

```bash
brew install tmux
```

### 2.5 WSL 2 注意事项

- 项目放在 `~/projects/OctoBot`，不要放在 `/mnt/c`。
- Windows 休眠或关机后，WSL 中的 OctoBot 也会停止。
- 需要 24/7 运行时，请关闭自动休眠，或改用专用 Linux 服务器/NAS。
- WSL 2 通常会自动把 `localhost:8000` 和 `localhost:5001` 转发到 Windows 浏览器。
- 可以在 Windows 用户目录创建或编辑 `C:\Users\<用户名>\.wslconfig` 限制资源：

```ini
[wsl2]
memory=4GB
processors=2
swap=2GB
```

保存后在 PowerShell 中执行 `wsl --shutdown`，再重新打开 Ubuntu。

## 3. Windows 原生安装

本章适用于不使用 WSL 的 Windows 10 2004+ 或 Windows 11。所有命令都在 **PowerShell** 中执行。

### 3.1 获取源码

以管理员身份运行 Powershell

```powershell
Set-Location $HOME
git clone https://github.com/Drakkar-Software/OctoBot.git
Set-Location .\OctoBot
```

如果需要使用开发分支：

```powershell
git checkout dev
```

### 3.2 安装 Python 与项目依赖
```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1
Set-Location $HOME\OctoBot
uv python install 3.13
uv sync --locked --python 3.13 --extra full --extra socks --group dev
```

uv 会在项目根目录创建 `.venv`。Windows 下虚拟环境入口位于 `.venv\Scripts`，但使用 `uv run` 时不需要手动激活。

如果安装过程中出现 C/C++ 编译错误，安装 Microsoft C++ Build Tools，并选择 **Desktop development with C++** 工作负载。只有需要从源码编译依赖时才需要该工具。

### 3.3 安装插件并启动

首次运行前安装全部插件：

```powershell
uv run --locked OctoBot tentacles --install --all
```

启动默认节点模式：

```powershell
uv run --locked OctoBot
```

启动后打开：

```text
http://localhost:8000
```

如果需要经典交易 Web 界面，使用 standalone 模式：

```powershell
uv run --locked OctoBot --standalone
```

此时打开：

```text
http://localhost:5001
```

### 3.4 后台运行与开机启动

简单方法是保持 PowerShell 或 Windows Terminal 窗口开启。如果需要登录 Windows 后自动启动，可以使用任务计划程序：

1. 打开 **任务计划程序**，选择 **创建任务**。
2. 在 **常规** 中选择 **只在用户登录时运行**。
3. 在 **触发器** 中新建 **登录时** 触发器。
4. 在 **操作** 中填写：

```text
程序或脚本：C:\Users\<用户名>\.local\bin\uv.exe
添加参数：run --locked OctoBot
起始于：C:\Users\<用户名>\OctoBot
```

5. 保存任务并手动运行一次，确认 OctoBot 可以正常启动。

可以先执行以下命令确认 `uv.exe` 的实际路径：

```powershell
(Get-Command uv).Source
```

### 3.5 Windows 端口设置

临时修改节点 API 端口：

```powershell
$env:NODE_API_PORT="8080"
uv run --locked OctoBot
```

临时修改 standalone 模式 Web 端口：

```powershell
$env:WEB_PORT="8080"
uv run --locked OctoBot --standalone
```

这些环境变量只对当前 PowerShell 会话有效。关闭终端后会自动失效。

### 3.6 Windows 使用提示

- 不要把项目放在 OneDrive 或其他同步目录中。
- 不要在运行中的 PowerShell 窗口里点击并选中日志文本。Windows 的 QuickEdit 模式可能暂停输出，导致程序表现为卡死；可在终端属性中关闭“快速编辑模式”。
- 需要长期运行时，使用任务计划程序或专用服务器，不要依赖休眠中的笔记本。
- 可以为项目目录添加 Windows Defender 排除项以降低扫描开销，但只应排除确切的仓库目录。

## 4. 使用 OctoBot

### 4.1 完成首次初始化

1. 在浏览器中打开本机 Web 界面。
2. 按页面指引完成节点初始化和钱包设置。
3. 如需使用 OctoBot 云端界面或移动应用，按初始化向导连接你的节点。
4. 在交易所创建 API 密钥，并添加到 OctoBot。建议只授予读取和交易权限，不要开启提现权限。

新版 OctoBot 默认以**节点模式**运行。节点是运行在你的电脑上的后端，负责保存配置、钱包和执行策略。

### 4.2 节点模式与手动 OctoBot

- **节点模式**：统一管理钱包、自动化任务和多个策略，是当前默认模式。
- **手动 OctoBot**：用于回测、Telegram、TradingView 以及其他经典工作流。可以在节点界面中点击 **New OctoBot** 创建。
- **Standalone 模式**：使用 `OctoBot --standalone` 启动经典单实例交易界面，适合回测、调试或直接使用传统 Web 界面。

### 4.3 先模拟，再实盘

建议先用模拟交易或回测验证策略，确认以下内容后再考虑真实资金：

- 交易所、交易对和手续费设置是否正确
- 策略在震荡、上涨和下跌行情中的表现
- 最大回撤、仓位大小和止损逻辑是否符合预期
- API 权限、网络和日志中是否存在异常

不要投入无法承受损失的资金。交易机器人不会消除市场风险。

## 5. 备份、更新与安全

### 5.1 备份数据

`user/` 目录包含策略、交易所配置和其他敏感信息，`tentacles/` 包含已安装插件。Linux、macOS 和 WSL 可以使用：

```bash
cd "$HOME/projects/OctoBot"
tar -czf "$HOME/octobot-backup-$(date +%F).tar.gz" user tentacles
```

Windows PowerShell 可以使用：

```powershell
Set-Location $HOME\OctoBot
Compress-Archive -Path user,tentacles -DestinationPath "$HOME\octobot-backup-$(Get-Date -Format yyyy-MM-dd).zip"
```

备份文件可能包含 API 密钥等敏感数据，不要上传到公共仓库或网盘。恢复时先停止 OctoBot，再解压覆盖 `user/` 和 `tentacles/` 后重新启动。

### 5.2 安全建议

- 不要直接把 `5001` 或 `8000` 端口暴露到公网。
- 需要远程访问时，优先使用 Tailscale 等私有网络，而不是公网端口转发。
- 为手动 OctoBot 的 Web 界面设置密码。
- 交易所 API 密钥只授予必要权限，并尽量配置 IP 白名单。
- 不要把 `user/config.json`、API 密钥、日志或备份文件提交到 Git。
- 不要使用管理员/root 权限运行 OctoBot，除非你明确知道原因。

## 6. 常见问题

### 6.1 `uv sync` 下载依赖很慢或无法连接

确认网络可以访问 PyPI：

```bash
curl -I https://pypi.org/simple/
```

Windows PowerShell：

```powershell
Invoke-WebRequest -Method Head https://pypi.org/simple/
```

公司代理、DNS 或防火墙可能拦截 Python 包和 GitHub 下载。修复网络后重新执行：

```bash
uv sync --locked --python 3.13 --extra full --extra socks --group dev
```

uv 会复用已经下载的缓存，未完成的部分会继续安装。

### 6.2 Python 版本不符合要求

```bash
uv python list
uv run python --version
uv python install 3.13
```

OctoBot 要求 Python 3.13 或更高版本。不要用 Python 3.10 或 3.11 代替。

### 6.3 `uv.lock` 与 `pyproject.toml` 不一致

正常安装应使用：

```bash
uv sync --locked --extra full --extra socks --group dev
```

如果刚修改了 `pyproject.toml`，需要先重新生成锁文件：

```bash
uv lock
uv sync --extra full --extra socks --group dev
```

不要手动编辑 `uv.lock`。

### 6.4 端口冲突

Linux、macOS 和 WSL：

```bash
NODE_API_PORT=8080 uv run --locked OctoBot
WEB_PORT=8080 uv run --locked OctoBot --standalone
```

Windows PowerShell：

```powershell
$env:NODE_API_PORT="8080"
uv run --locked OctoBot

$env:WEB_PORT="8080"
uv run --locked OctoBot --standalone
```

在 Windows 中查看端口占用：

```powershell
netstat -ano | findstr :5001
netstat -ano | findstr :8000
```

停止占用端口的程序，或使用上面的环境变量更换端口。

### 6.5 浏览器打不开 `http://localhost`

确认 OctoBot 进程仍在运行，并检查终端中的 Web 服务启动日志。可以尝试：

- `http://127.0.0.1:8000`
- `http://127.0.0.1:5001`
- WSL 中执行 `hostname -I` 后使用 WSL IP 访问

同时检查系统防火墙、VPN 或安全软件是否拦截连接。

### 6.6 编译依赖失败

Linux/WSL 安装编译工具：

```bash
sudo apt install -y build-essential rustc cargo
```

macOS 确认命令行工具和 Rust 可用：

```bash
xcode-select --install
source "$HOME/.cargo/env"
```

Windows 安装 Microsoft C++ Build Tools，并选择 **Desktop development with C++** 工作负载。

### 6.7 WSL 文件监听、安装或回测异常

确认项目位于 WSL Linux 文件系统，例如 `~/projects/OctoBot`，而不是 `/mnt/c`。如果项目已经在 Windows 目录，移动到 Linux 家目录后重新执行：

```bash
uv sync --locked --python 3.13 --extra full --extra socks --group dev
```

### 6.8 回测或安装依赖时内存不足

关闭其他占用内存的应用，避免同时运行多个回测。WSL 用户可增大 `.wslconfig` 中的 `memory`，然后执行 `wsl --shutdown` 并重新打开 Ubuntu。

### 6.9 交易所请求提示时间戳或签名错误

长期休眠或挂起 WSL 后，Linux 时钟可能发生偏移。建议先执行 `wsl --shutdown`，再重新打开 Ubuntu，让 WSL 重新同步时间；同时确认 Windows 的“自动设置时间”已开启。

部分 WSL 发行版可以尝试手动校准：

```bash
sudo hwclock -s
```

Windows 原生环境请确认系统的日期、时间和时区设置正确。

## 7. 参考资料

- [uv 项目管理文档](https://docs.astral.sh/uv/concepts/projects/)
- [Git 安装文档](https://git-scm.com/downloads)
- [OctoBot 中文 README](README-CN.md)
- [OctoBot 节点模式入门](docs/content/guides/octobot-beta-getting-started.md)
- [OctoBot 常见问题与排错](docs/content/guides/octobot-installation/octobot-troubleshoot.md)
