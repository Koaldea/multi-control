"""Multi-Control 启动入口.

用法:
    python main.py host                # 被控端（共享桌面）
    python main.py viewer              # 控制端（自动发现）
    python main.py viewer 192.168.1.5  # 控制端（直连指定IP）
"""

import argparse


def main():
    parser = argparse.ArgumentParser(description="Multi-Control — 多人独立光标键盘远程协作")
    sub = parser.add_subparsers(dest="mode", required=True)

    sub.add_parser("host", help="启动被控端（共享桌面）")

    viewer_parser = sub.add_parser("viewer", help="启动控制端（连接远程桌面）")
    viewer_parser.add_argument("host_ip", nargs="?", default=None,
                               help="被控端 IP（留空则自动发现）")

    args = parser.parse_args()

    if args.mode == "host":
        from multi_control.host.server import run_host
        run_host()
    elif args.mode == "viewer":
        from multi_control.viewer.client import run_viewer
        run_viewer(args.host_ip)


if __name__ == "__main__":
    main()
