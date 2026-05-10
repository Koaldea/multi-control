# Multi-Control

**多人独立光标键盘远程协作工具** — 基于 Windows 的局域网远程桌面方案。

被控端共享桌面，控制端实时查看并操作。双方拥有**独立的光标和键盘**，可同时操作同一台电脑的同一个焦点窗口，互不干扰。

## 功能

- **独立光标** — 远程控制端的光标在被控端上以红色箭头显示，与本地光标区分
- **独立键盘** — 双方可同时按键，输入合流到同一焦点窗口（适合结对编程、协作编辑）
- **低延迟画面** — DXCam (DXGI) GPU 屏幕采集 + JPEG 压缩 + 帧差传输
- **局域网自动发现** — UDP 广播自动发现被控端，无需配置 IP
- **单文件分发** — 打包为单个 exe，无需安装 Python 环境

## 快速开始

### 打包后使用

```
Multi-Control.exe host        # 启动被控端（共享桌面）
Multi-Control.exe viewer      # 自动发现并连接
Multi-Control.exe viewer 192.168.1.5  # 直连
```

### 源码运行

```bash
pip install -r requirements.txt
python main.py host           # 启动被控端
python main.py viewer         # 自动发现并连接
python main.py viewer 192.168.1.5  # 直连指定 IP
```

## 架构

```
被控端 (Host)                          控制端 (Viewer)
─────────────                          ──────────────
DXCam → JPEG → ZMQ PUB ────────────→ ZMQ SUB → 解码 → Pygame 渲染
   ↑                                            ↓
   │                                       Pygame 事件循环
   │                                       捕获本地键鼠事件
   ↓                                            ↓
ZMQ ROUTER ←──────────────────────────── ZMQ DEALER
   ↓
PostMessage → 直接发送到目标窗口（不碰系统光标）
GDI 覆盖层 → 渲染远程红色光标
   ↓
远程光标不干扰被控端本地操作
```

| 模块 | 技术栈 |
|------|--------|
| 屏幕采集 | DXCam (DXGI) |
| 图像压缩 | OpenCV (JPEG) |
| 网络传输 | ZeroMQ (PUB/SUB + DEALER/ROUTER) |
| 输入注入 | Win32 PostMessage（独立光标） |
| 远程光标 | GDI 透明覆盖窗口 |
| 控制端 UI | Pygame |
| 被控端面板 | PyQt6 |
| LAN 发现 | UDP 广播 |

## 系统要求

- Windows 10/11（需要管理员权限运行被控端）
- 局域网环境

## 开发

```bash
pip install -r requirements.txt
```

打包：

```bash
pip install pyinstaller
pyinstaller --name "Multi-Control" --onefile --clean --noconfirm --console main.py
```
