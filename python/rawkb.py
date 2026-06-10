"""
Win32 原始键盘输入

使用 GetAsyncKeyState 轮询硬件按键状态。
不依赖 msvcrt 缓冲区，不会丢失按键，支持方向键等特殊键。
"""

import sys
from typing import Dict, Set

# 仅 Windows 可用
if sys.platform == 'win32':
    import ctypes
    from ctypes import wintypes

    _user32 = ctypes.windll.user32
    _user32.GetAsyncKeyState.argtypes = [wintypes.INT]
    _user32.GetAsyncKeyState.restype = wintypes.SHORT

    def _is_down(vk: int) -> bool:
        """检查某个虚拟键是否当前按下 (最高位=1 表示按下)"""
        state = _user32.GetAsyncKeyState(vk)
        return (state & 0x8000) != 0

    def _was_pressed(vk: int) -> bool:
        """检查某个键自上次调用以来是否被按下过 (最低位=1)"""
        state = _user32.GetAsyncKeyState(vk)
        return (state & 0x0001) != 0
else:
    def _is_down(vk: int) -> bool:
        return False

    def _was_pressed(vk: int) -> bool:
        return False


# 虚拟键码 (VK) 常量
VK_BACK       = 0x08
VK_TAB        = 0x09
VK_RETURN     = 0x0D
VK_SHIFT      = 0x10
VK_CONTROL    = 0x11
VK_MENU       = 0x12  # Alt
VK_ESCAPE     = 0x1B
VK_SPACE      = 0x20
VK_LEFT       = 0x25
VK_UP         = 0x26
VK_RIGHT      = 0x27
VK_DOWN       = 0x28
VK_0          = 0x30
VK_A          = 0x41
VK_F1         = 0x70

# ASCII 字符 -> VK 映射 (小写字母 + 数字 + 常用符号)
_CHAR_TO_VK: Dict[str, int] = {}
for _c in 'abcdefghijklmnopqrstuvwxyz':
    _CHAR_TO_VK[_c] = VK_A + ord(_c) - ord('a')
    _CHAR_TO_VK[_c.upper()] = VK_A + ord(_c) - ord('a')
for _c in '0123456789':
    _CHAR_TO_VK[_c] = VK_0 + ord(_c) - ord('0')
_CHAR_TO_VK[' ']     = VK_SPACE
_CHAR_TO_VK['\r']    = VK_RETURN
_CHAR_TO_VK['\n']    = VK_RETURN
_CHAR_TO_VK['\x1b']  = VK_ESCAPE
_CHAR_TO_VK['\t']    = VK_TAB
_CHAR_TO_VK['\x08']  = VK_BACK

# 名称 -> VK 映射 (用于 is_key_pressed("left") 等)
_NAME_TO_VK: Dict[str, int] = {
    'left':      VK_LEFT,
    'right':     VK_RIGHT,
    'up':        VK_UP,
    'down':      VK_DOWN,
    'space':     VK_SPACE,
    'enter':     VK_RETURN,
    'return':    VK_RETURN,
    'esc':       VK_ESCAPE,
    'escape':    VK_ESCAPE,
    'tab':       VK_TAB,
    'backspace': VK_BACK,
    'shift':     VK_SHIFT,
    'ctrl':      VK_CONTROL,
    'alt':       VK_MENU,
}


def _resolve_vk(key: str) -> int:
    """将按键名解析为 VK 码"""
    # 先查名称表
    if key.lower() in _NAME_TO_VK:
        return _NAME_TO_VK[key.lower()]
    # 再查字符表
    if key in _CHAR_TO_VK:
        return _CHAR_TO_VK[key]
    # F1-F12
    if key.upper().startswith('F') and key[1:].isdigit():
        n = int(key[1:])
        if 1 <= n <= 12:
            return VK_F1 + n - 1
    return -1


class RawKeyboard:
    """
    Win32 原始键盘输入

    使用方法:
        kb = RawKeyboard()
        while True:
            kb.poll()
            if kb.is_down('a'):
                move_left()
            if kb.just_pressed('space'):
                jump()
            if kb.is_down('left'):
                move_left()
            if kb.is_down('right'):
                move_right()
    """

    def __init__(self):
        self._prev: Dict[int, bool] = {}   # 上一帧各 VK 状态
        self._curr: Dict[int, bool] = {}   # 当前帧各 VK 状态
        self._just_pressed: Set[int] = set()
        self._just_released: Set[int] = set()

        # 预热：查询所有常用键的初始状态
        if sys.platform == 'win32':
            for vk in list(_CHAR_TO_VK.values()) + list(_NAME_TO_VK.values()):
                self._prev[vk] = _is_down(vk)

    def poll(self):
        """每帧调用一次，刷新按键状态"""
        self._just_pressed.clear()
        self._just_released.clear()

        if sys.platform != 'win32':
            return

        # 收集所有关心的 VK 码
        all_vks = set(_CHAR_TO_VK.values()) | set(_NAME_TO_VK.values())
        # 也追踪上一帧按下的键
        all_vks |= set(self._prev.keys())

        for vk in all_vks:
            was = self._prev.get(vk, False)
            now = _is_down(vk)
            self._curr[vk] = now
            if now and not was:
                self._just_pressed.add(vk)
            elif was and not now:
                self._just_released.add(vk)

        self._prev = dict(self._curr)

    def is_down(self, key: str) -> bool:
        """当前是否按住该键"""
        vk = _resolve_vk(key)
        return self._curr.get(vk, False) if vk >= 0 else False

    def just_pressed(self, key: str) -> bool:
        """本帧是否刚按下该键"""
        vk = _resolve_vk(key)
        return vk in self._just_pressed if vk >= 0 else False

    def just_released(self, key: str) -> bool:
        """本帧是否刚松开该键"""
        vk = _resolve_vk(key)
        return vk in self._just_released if vk >= 0 else False
