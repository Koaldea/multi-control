"""Pygame 键鼠事件捕获 → 打包 → 发送到被控端."""

from typing import Optional

import pygame

from .display import RemoteDisplay
from ..network.command import CommandSender


# Pygame key constant → Windows 虚拟键码 (VK)
_KEY_MAP: dict[int, int] = {
    pygame.K_BACKSPACE: 0x08,
    pygame.K_TAB: 0x09,
    pygame.K_RETURN: 0x0D,
    pygame.K_ESCAPE: 0x1B,
    pygame.K_SPACE: 0x20,
    pygame.K_EXCLAIM: 0x31,
    pygame.K_QUOTEDBL: 0xDE,
    pygame.K_HASH: 0x33,
    pygame.K_DOLLAR: 0x34,
    pygame.K_AMPERSAND: 0x37,
    pygame.K_QUOTE: 0xDE,
    pygame.K_LEFTPAREN: 0x39,
    pygame.K_RIGHTPAREN: 0x30,
    pygame.K_ASTERISK: 0x38,
    pygame.K_PLUS: 0xBB,
    pygame.K_COMMA: 0xBC,
    pygame.K_MINUS: 0xBD,
    pygame.K_PERIOD: 0xBE,
    pygame.K_SLASH: 0xBF,
    pygame.K_0: 0x30,
    pygame.K_1: 0x31,
    pygame.K_2: 0x32,
    pygame.K_3: 0x33,
    pygame.K_4: 0x34,
    pygame.K_5: 0x35,
    pygame.K_6: 0x36,
    pygame.K_7: 0x37,
    pygame.K_8: 0x38,
    pygame.K_9: 0x39,
    pygame.K_COLON: 0xBA,
    pygame.K_SEMICOLON: 0xBA,
    pygame.K_LESS: 0xBC,
    pygame.K_EQUALS: 0xBB,
    pygame.K_GREATER: 0xBE,
    pygame.K_QUESTION: 0xBF,
    pygame.K_AT: 0x32,
    pygame.K_LEFTBRACKET: 0xDB,
    pygame.K_BACKSLASH: 0xDC,
    pygame.K_RIGHTBRACKET: 0xDD,
    pygame.K_CARET: 0x36,
    pygame.K_UNDERSCORE: 0xBD,
    pygame.K_BACKQUOTE: 0xC0,
    pygame.K_a: 0x41,
    pygame.K_b: 0x42,
    pygame.K_c: 0x43,
    pygame.K_d: 0x44,
    pygame.K_e: 0x45,
    pygame.K_f: 0x46,
    pygame.K_g: 0x47,
    pygame.K_h: 0x48,
    pygame.K_i: 0x49,
    pygame.K_j: 0x4A,
    pygame.K_k: 0x4B,
    pygame.K_l: 0x4C,
    pygame.K_m: 0x4D,
    pygame.K_n: 0x4E,
    pygame.K_o: 0x4F,
    pygame.K_p: 0x50,
    pygame.K_q: 0x51,
    pygame.K_r: 0x52,
    pygame.K_s: 0x53,
    pygame.K_t: 0x54,
    pygame.K_u: 0x55,
    pygame.K_v: 0x56,
    pygame.K_w: 0x57,
    pygame.K_x: 0x58,
    pygame.K_y: 0x59,
    pygame.K_z: 0x5A,
    pygame.K_DELETE: 0x2E,
    pygame.K_KP0: 0x60,
    pygame.K_KP1: 0x61,
    pygame.K_KP2: 0x62,
    pygame.K_KP3: 0x63,
    pygame.K_KP4: 0x64,
    pygame.K_KP5: 0x65,
    pygame.K_KP6: 0x66,
    pygame.K_KP7: 0x67,
    pygame.K_KP8: 0x68,
    pygame.K_KP9: 0x69,
    pygame.K_KP_PERIOD: 0x6E,
    pygame.K_KP_DIVIDE: 0x6F,
    pygame.K_KP_MULTIPLY: 0x6A,
    pygame.K_KP_MINUS: 0x6D,
    pygame.K_KP_PLUS: 0x6B,
    pygame.K_KP_ENTER: 0x0D,
    pygame.K_UP: 0x26,
    pygame.K_DOWN: 0x28,
    pygame.K_LEFT: 0x25,
    pygame.K_RIGHT: 0x27,
    pygame.K_HOME: 0x24,
    pygame.K_END: 0x23,
    pygame.K_PAGEUP: 0x21,
    pygame.K_PAGEDOWN: 0x22,
    pygame.K_INSERT: 0x2D,
    pygame.K_F1: 0x70,
    pygame.K_F2: 0x71,
    pygame.K_F3: 0x72,
    pygame.K_F4: 0x73,
    pygame.K_F5: 0x74,
    pygame.K_F6: 0x75,
    pygame.K_F7: 0x76,
    pygame.K_F8: 0x77,
    pygame.K_F9: 0x78,
    pygame.K_F10: 0x79,
    pygame.K_F11: 0x7A,
    pygame.K_F12: 0x7B,
    pygame.K_LSHIFT: 0xA0,
    pygame.K_RSHIFT: 0xA1,
    pygame.K_LCTRL: 0xA2,
    pygame.K_RCTRL: 0xA3,
    pygame.K_LALT: 0xA4,
    pygame.K_RALT: 0xA5,
    pygame.K_LSUPER: 0x5B,
    pygame.K_RSUPER: 0x5C,
    pygame.K_CAPSLOCK: 0x14,
    pygame.K_NUMLOCK: 0x90,
    pygame.K_SCROLLOCK: 0x91,
}

# 特殊键：shift 状态下输出不同字符的键
_SHIFTED_KEYS = {
    pygame.K_1: (0x31, "!"),
    pygame.K_2: (0x32, "@"),
    pygame.K_3: (0x33, "#"),
    pygame.K_4: (0x34, "$"),
    pygame.K_5: (0x35, "%"),
    pygame.K_6: (0x36, "^"),
    pygame.K_7: (0x37, "&"),
    pygame.K_8: (0x38, "*"),
    pygame.K_9: (0x39, "("),
    pygame.K_0: (0x30, ")"),
    pygame.K_MINUS: (0xBD, "_"),
    pygame.K_EQUALS: (0xBB, "+"),
    pygame.K_LEFTBRACKET: (0xDB, "{"),
    pygame.K_RIGHTBRACKET: (0xDD, "}"),
    pygame.K_BACKSLASH: (0xDC, "|"),
    pygame.K_SEMICOLON: (0xBA, ":"),
    pygame.K_QUOTE: (0xDE, '"'),
    pygame.K_COMMA: (0xBC, "<"),
    pygame.K_PERIOD: (0xBE, ">"),
    pygame.K_SLASH: (0xBF, "?"),
    pygame.K_BACKQUOTE: (0xC0, "~"),
}


def map_pygame_key(pygame_key: int) -> Optional[int]:
    """Pygame 按键常量 → Windows 虚拟键码."""
    return _KEY_MAP.get(pygame_key)


class InputCapture:
    """捕获 Pygame 窗口中的本地键鼠事件，批量发送到被控端."""

    def __init__(self, display: RemoteDisplay, cmd_sender: CommandSender):
        self._display = display
        self._sender = cmd_sender
        self._events: list[dict] = []
        self._mouse_x = 0
        self._mouse_y = 0
        self._mouse_moved = False

    def collect_events(self) -> None:
        """从 Pygame 事件队列收集本帧的输入事件."""
        self._mouse_moved = False
        self._events.clear()

        event_list = pygame.event.get()
        self._display.event_count = len(event_list)

        for event in event_list:
            if event.type == pygame.QUIT:
                self._events.append({"type": "quit"})
                return
            elif event.type == pygame.KEYDOWN:
                self._events.append({"type": "key", "vk": map_pygame_key(event.key), "pressed": True})
                # 忽略 Esc（用于退出）
                if event.key == pygame.K_ESCAPE:
                    self._events.append({"type": "quit"})
                    return
            elif event.type == pygame.KEYUP:
                self._events.append({"type": "key", "vk": map_pygame_key(event.key), "pressed": False})
            elif event.type == pygame.MOUSEMOTION:
                # 换算到远程实际坐标
                win_w, win_h = pygame.display.get_surface().get_size()
                fw, fh = self._display.window_size
                if fw > 0 and fh > 0:
                    self._mouse_x = int(event.pos[0] * fw / win_w)
                    self._mouse_y = int(event.pos[1] * fh / win_h)
                    self._mouse_moved = True
            elif event.type == pygame.MOUSEBUTTONDOWN:
                btn = _map_button(event.button)
                if btn:
                    self._events.append({"type": "mouse_button", "button": btn, "pressed": True})
                if event.button in (4, 5):
                    delta = 1 if event.button == 4 else -1
                    self._events.append({"type": "mouse_wheel", "delta": delta})
            elif event.type == pygame.MOUSEBUTTONUP:
                btn = _map_button(event.button)
                if btn:
                    self._events.append({"type": "mouse_button", "button": btn, "pressed": False})
            elif event.type == pygame.WINDOWRESIZED:
                pass  # Pygame 自动处理缩放

        # 合并鼠标移动（每帧最多发一次）
        if self._mouse_moved:
            self._events.insert(0, {"type": "mouse_move", "x": self._mouse_x, "y": self._mouse_y})

    def flush(self) -> None:
        """发送积累的事件."""
        if self._events:
            self._sender.send_input(self._events)


def _map_button(pygame_button: int) -> Optional[str]:
    """Pygame 鼠标按键 → 字符串."""
    return {1: "left", 2: "middle", 3: "right"}.get(pygame_button)
