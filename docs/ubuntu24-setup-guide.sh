#!/bin/bash
# ============================================================
# Ubuntu 24.04 LTS 新服务器初始化配置脚本
# 适用于：云服务器 / VPS 首次连接后执行
# ============================================================

set -e

# 检查是否 root，提示用 sudo
if [ "$(id -u)" -eq 0 ]; then
    echo "⚠️  请不要用 root 直接运行，用普通用户 + sudo"
    exit 1
fi

echo "=========================================="
echo " Ubuntu 24.04 LTS 服务器初始化"
echo "=========================================="

# ---- 0. 配置国内镜像源 (阿里云) ----
echo ""
echo "[0/9] 配置阿里云镜像源..."
sudo cp /etc/apt/sources.list.d/ubuntu.sources /etc/apt/sources.list.d/ubuntu.sources.bak 2>/dev/null || true
sudo tee /etc/apt/sources.list.d/ubuntu.sources > /dev/null << 'EOF'
Types: deb
URIs: https://mirrors.aliyun.com/ubuntu
Suites: noble noble-updates noble-security
Components: main restricted universe multiverse
Signed-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg

Types: deb-src
URIs: https://mirrors.aliyun.com/ubuntu
Suites: noble noble-updates noble-security
Components: main restricted universe multiverse
Signed-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg
EOF
echo "镜像源已切换为阿里云"

# ---- 1. 系统更新 ----
echo ""
echo "[1/9] 更新系统包..."
sudo apt update && sudo apt upgrade -y

# ---- 2. 基础必装工具 ----
echo ""
echo "[2/9] 安装基础工具..."
sudo apt install -y \
    curl \
    wget \
    git \
    nano \
    htop \
    unzip \
    zip \
    jq \
    lsof \
    software-properties-common \
    apt-transport-https \
    ca-certificates \
    gnupg

# 设置默认编辑器为 nano
sudo update-alternatives --set editor /usr/bin/nano 2>/dev/null || true

# Python3：系统自带 Python 3.14 + venv，pip 用 ensurepip 安装
python3 -m ensurepip --upgrade 2>/dev/null || echo "pip 已可用或稍后手动安装"

# ---- 3. Node.js 安装 (LTS) ----
echo ""
echo "[3/9] 安装 Node.js 22 LTS..."
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo bash -
sudo apt install -y nodejs
echo "Node.js: $(node --version)"
echo "npm: $(npm --version)"

# 配置 npm 国内镜像
npm config set registry https://registry.npmmirror.com

# ---- 4. 防火墙配置 (UFW) ----
echo ""
echo "[4/9] 配置防火墙..."
sudo apt install -y ufw
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh          # 22
sudo ufw allow 80/tcp       # HTTP
sudo ufw allow 443/tcp      # HTTPS
# 按需开放更多端口，取消注释：
# sudo ufw allow 8000/tcp   # 后端 API
# sudo ufw allow 8001/tcp   # 后端 API
# sudo ufw allow 3000/tcp   # 前端开发
# sudo ufw allow 5173/tcp   # Vite 开发服务器
sudo ufw --force enable
echo "防火墙已启用"
sudo ufw status verbose

# ---- 5. SSH 安全加固 ----
echo ""
echo "[5/9] SSH 安全加固..."
sudo cp /etc/ssh/sshd_config /etc/ssh/sshd_config.bak

# 禁用 root 登录
sudo sed -i 's/^#\?PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config
# 禁用密码登录（确保你先配好 SSH Key 再取消注释！）
# sudo sed -i 's/^#\?PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config

sudo systemctl restart sshd
echo "SSH 已加固：禁止 root 登录"

# ---- 6. 时区与时间同步 ----
echo ""
echo "[6/9] 设置时区与时间同步..."
sudo timedatectl set-timezone Asia/Shanghai
sudo timedatectl set-ntp true
echo "当前时间: $(date '+%Y-%m-%d %H:%M:%S %Z')"

# ---- 7. Swap 配置 ----
echo ""
echo "[7/9] 配置 Swap..."
CURRENT_SWAP=$(free -m | awk '/^Swap:/ {print $2}')
if [ -z "$CURRENT_SWAP" ] || [ "$CURRENT_SWAP" -lt 1024 ]; then
    if [ ! -f /swapfile ]; then
        echo "创建 4GB Swap..."
        sudo fallocate -l 4G /swapfile
        sudo chmod 600 /swapfile
        sudo mkswap /swapfile
        sudo swapon /swapfile
        if ! grep -q '/swapfile' /etc/fstab; then
            echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
        fi
    else
        echo "/swapfile 已存在，跳过创建"
    fi
    # sysctl 参数
    if ! grep -q 'vm.swappiness' /etc/sysctl.conf; then
        echo "vm.swappiness=10" | sudo tee -a /etc/sysctl.conf
    else
        sudo sed -i 's/vm.swappiness=.*/vm.swappiness=10/' /etc/sysctl.conf
    fi
    if ! grep -q 'vm.vfs_cache_pressure' /etc/sysctl.conf; then
        echo "vm.vfs_cache_pressure=50" | sudo tee -a /etc/sysctl.conf
    else
        sudo sed -i 's/vm.vfs_cache_pressure=.*/vm.vfs_cache_pressure=50/' /etc/sysctl.conf
    fi
    sudo sysctl -p 2>/dev/null
    echo "Swap 已配置"
else
    echo "Swap 已存在 (${CURRENT_SWAP}MB)，跳过"
fi
free -h | grep Swap

# ---- 8. Docker 安装（阿里云镜像源，国内可用） ----
echo ""
echo "[8/9] 安装 Docker (阿里云源)..."
if ! command -v docker &> /dev/null; then
    # 添加阿里云 Docker GPG 密钥和仓库
    sudo install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://mirrors.aliyun.com/docker-ce/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker-aliyun.gpg
    sudo chmod a+r /etc/apt/keyrings/docker-aliyun.gpg
    echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/docker-aliyun.gpg] https://mirrors.aliyun.com/docker-ce/linux/ubuntu noble stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    sudo apt update
    sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
    sudo usermod -aG docker $USER
    echo "Docker 已安装（阿里云源），当前用户已加入 docker 组"
    docker --version
    docker compose version
else
    echo "Docker 已存在: $(docker --version)"
fi

# 配置 Docker 国内镜像加速 + 日志限制
echo ""
echo "配置 Docker 镜像加速..."
sudo mkdir -p /etc/docker
if [ ! -f /etc/docker/daemon.json ]; then
    sudo tee /etc/docker/daemon.json > /dev/null << 'EOF'
{
    "registry-mirrors": [
        "https://docker.1ms.run",
        "https://docker.xuanyuan.me"
    ],
    "log-driver": "json-file",
    "log-opts": {
        "max-size": "10m",
        "max-file": "3"
    }
}
EOF
    sudo systemctl daemon-reload
    sudo systemctl restart docker
    echo "Docker 镜像加速已配置"
else
    echo "/etc/docker/daemon.json 已存在，跳过"
fi

# ---- 9. 系统优化 + pip 镜像 ----
echo ""
echo "[9/9] 系统优化..."

# 限制 journald 日志大小
sudo mkdir -p /etc/systemd/journald.conf.d
sudo tee /etc/systemd/journald.conf.d/99-size.conf > /dev/null << 'EOF'
[Journal]
SystemMaxUse=200M
MaxRetentionSec=7day
EOF
sudo systemctl restart systemd-journald

# pip 国内镜像
mkdir -p ~/.config/pip
tee ~/.config/pip/pip.conf > /dev/null << 'EOF'
[global]
index-url = https://mirrors.aliyun.com/pypi/simple/
trusted-host = mirrors.aliyun.com
EOF
echo "pip 镜像已配置为阿里云"

# 清理不需要的包
sudo apt autoremove -y
sudo apt autoclean

# ---- 完成 ----
echo ""
echo "=========================================="
echo " ✅ 初始化完成！"
echo "=========================================="
echo ""
echo "⚠️  重要提醒："
echo "  1. 重新登录 SSH 使 docker 组生效"
echo "  2. 建议尽快配置 SSH Key 并禁用密码登录"
echo ""
echo "系统信息："
echo "  内核:  $(uname -r)"
echo "  CPU:   $(nproc) 核"
free -h | awk '/^Mem:/ {print "  内存:  " $2}'
df -h / | tail -1 | awk '{print "  磁盘:  " $2 " (已用 " $3 ")"}'
echo ""
