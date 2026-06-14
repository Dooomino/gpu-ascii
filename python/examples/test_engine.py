"""
快速测试新功能
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from gpu_ascii import (
    GpuAscii, GameRenderer, GameLoop, InputManager,
    SpriteSheet, SpriteAnimator
)

def test_game_loop():
    """测试GameLoop"""
    print("测试GameLoop...", flush=True)
    game_loop = GameLoop(target_fps=60)
    
    for i in range(10):
        game_loop.begin_frame()
        # 模拟一些工作
        import time
        time.sleep(0.001)
        game_loop.end_frame()
    
    print(f"  FPS: {game_loop.fps:.1f}")
    print(f"  帧数: {game_loop.frame_count}")
    print("  OK")

def test_input_manager():
    """测试InputManager"""
    print("测试InputManager...", flush=True)
    input_mgr = InputManager()
    
    # 测试基本功能
    assert not input_mgr.is_key_pressed('a')
    assert not input_mgr.is_key_just_pressed('a')
    
    print("  OK")

def test_sprite_sheet():
    """测试SpriteSheet"""
    print("测试SpriteSheet...", flush=True)
    
    gif_dir = Path(__file__).parent / "test_gif"
    if not gif_dir.exists():
        print("  跳过（找不到test_gif目录）")
        return
    
    sprite_sheet = SpriteSheet.from_gif_frames(str(gif_dir))
    print(f"  帧数: {sprite_sheet.frame_count}")
    
    # 测试动画器
    animator = SpriteAnimator(sprite_sheet, frame_rate=20.0, loop=True)
    for i in range(5):
        animator.update(0.05)
    
    print(f"  当前帧: {animator.current_frame_index}")
    print("  OK")

def test_game_renderer():
    """测试GameRenderer"""
    print("测试GameRenderer...", flush=True)
    
    gpu = GpuAscii()
    renderer = GameRenderer(gpu)
    
    # 测试初始化
    renderer.init_debug()
    
    # 测试帧计数
    assert renderer.get_frame_count() == 0
    
    # 清理
    renderer.cleanup()
    
    print("  OK")

def main():
    print("=" * 40)
    print("GPU-ASCII 游戏引擎功能测试")
    print("=" * 40)
    print()
    
    test_game_loop()
    print()
    
    test_input_manager()
    print()
    
    test_sprite_sheet()
    print()
    
    test_game_renderer()
    print()
    
    print("=" * 40)
    print("所有测试通过!")
    print("=" * 40)

if __name__ == "__main__":
    main()
