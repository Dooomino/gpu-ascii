"""
GPU ASCII - GPU加速的图像转ASCII游戏引擎
"""

from .gpu_ascii import GpuAscii, GameRenderer, image_to_ascii, AsciiResult, FrameInfo, get_terminal_size
from .game_loop import GameLoop, Clock
from .input_manager import InputManager, KeyReader, Event, EventType
from .scene_manager import Scene, SceneManager
from .sprite_animation import SpriteSheet, SpriteAnimator, SpriteFrame

__version__ = "0.2.0"
__all__ = [
    # 核心
    "GpuAscii",
    "GameRenderer",
    "image_to_ascii",
    "AsciiResult",
    "FrameInfo",
    "get_terminal_size",
    # 游戏循环
    "GameLoop",
    "Clock",
    # 输入
    "InputManager",
    "KeyReader",
    "Event",
    "EventType",
    # 场景
    "Scene",
    "SceneManager",
    # 动画
    "SpriteSheet",
    "SpriteAnimator",
    "SpriteFrame",
]
