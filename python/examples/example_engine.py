"""
游戏引擎综合示例 - 展示所有新功能

功能演示:
1. GameLoop - 帧时间管理
2. InputManager - 键盘输入
3. SceneManager - 场景管理
4. SpriteSheet/Animator - 精灵动画
5. GameRenderer - 游戏模式渲染

运行方式:
    python example_engine.py
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from gpu_ascii import (
    GpuAscii, GameRenderer, GameLoop, InputManager, KeyReader,
    Scene, SceneManager, SpriteSheet, SpriteAnimator,
    EventType, Event
)


# ==================== 场景定义 ====================

class MenuScene(Scene):
    """菜单场景"""
    
    def __init__(self):
        super().__init__("menu")
        self.selected = 0
        self.options = ["开始游戏", "退出"]
    
    def on_enter(self):
        print("进入菜单场景")
    
    def update(self, delta_time: float):
        pass
    
    def render(self, renderer):
        # 菜单渲染逻辑
        pass


class GameScene(Scene):
    """游戏场景"""
    
    def __init__(self, gif_dir: str):
        super().__init__("game")
        self.gif_dir = gif_dir
        self.sprite_sheet = None
        self.animator = None
    
    def on_enter(self):
        print("进入游戏场景")
        # 加载精灵表
        self.sprite_sheet = SpriteSheet.from_gif_frames(self.gif_dir)
        self.animator = SpriteAnimator(self.sprite_sheet, frame_rate=20.0, loop=True)
        print(f"加载了 {self.sprite_sheet.frame_count} 帧")
    
    def update(self, delta_time: float):
        if self.animator:
            self.animator.update(delta_time)
    
    def render(self, renderer):
        if self.animator:
            frame = self.animator.get_current_frame()
            renderer.update_to_terminal(frame.path)


class DemoScene(Scene):
    """演示场景 - 展示基本功能"""
    
    def __init__(self, image_path: str):
        super().__init__("demo")
        self.image_path = image_path
    
    def update(self, delta_time: float):
        pass
    
    def render(self, renderer):
        renderer.update_to_terminal(self.image_path)


# ==================== 主程序 ====================

def main():
    """主函数"""
    print("=" * 50)
    print("GPU-ASCII 游戏引擎 v0.2.0")
    print("=" * 50)
    print()
    
    # 查找资源
    script_dir = Path(__file__).parent
    gif_dir = script_dir / "test_gif"
    test_image = script_dir / "test.png"
    
    if not gif_dir.exists():
        print(f"错误: 找不到GIF目录 {gif_dir}")
        return
    
    print("初始化组件...")
    
    # 初始化核心组件
    gpu = GpuAscii()
    renderer = GameRenderer(gpu)
    game_loop = GameLoop(target_fps=20)
    input_mgr = InputManager()
    scene_mgr = SceneManager()
    
    print("组件初始化完成")
    print()
    print("操作说明:")
    print("  按 'q' - 退出")
    print("  按 '1' - 切换到演示场景")
    print("  按 '2' - 切换到游戏场景")
    print()
    input("按回车开始...")
    
    # 创建初始场景
    if test_image.exists():
        scene_mgr.push_scene(DemoScene(str(test_image)))
    else:
        scene_mgr.push_scene(GameScene(str(gif_dir)))
    
    # 初始化渲染器（调试模式）
    renderer.init_debug()
    
    frame_count = 0
    start_time = time.time()
    
    try:
        while game_loop.begin_frame():
            # 更新输入
            input_mgr.update()
            
            # 检查退出
            if input_mgr.is_key_pressed('q') or input_mgr.is_key_just_pressed('q'):
                break
            
            # 场景切换
            if input_mgr.is_key_just_pressed('1'):
                if test_image.exists():
                    scene_mgr.switch_scene(DemoScene(str(test_image)))
                    print("切换到演示场景", file=sys.stderr)
            
            if input_mgr.is_key_just_pressed('2'):
                scene_mgr.switch_scene(GameScene(str(gif_dir)))
                print("切换到游戏场景", file=sys.stderr)
            
            # 更新场景
            scene_mgr.update(game_loop.delta_time)
            
            # 渲染场景
            scene_mgr.render(renderer)
            
            frame_count += 1
            
            # 显示FPS（每30帧）
            if frame_count % 30 == 0:
                fps = game_loop.fps
                print(f"FPS: {fps:.1f}, Frame: {frame_count}", file=sys.stderr)
            
            game_loop.end_frame()
    
    except KeyboardInterrupt:
        print("\n用户中断")
    
    finally:
        # 清理
        renderer.cleanup()
        
        elapsed = time.time() - start_time
        avg_fps = frame_count / elapsed if elapsed > 0 else 0
        
        print()
        print("=" * 50)
        print("运行统计:")
        print(f"  总帧数: {frame_count}")
        print(f"  运行时间: {elapsed:.2f}秒")
        print(f"  平均帧率: {avg_fps:.1f} FPS")
        print("=" * 50)


if __name__ == "__main__":
    main()
