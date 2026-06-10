"""
游戏模式演示 - 单页面动态刷新

演示内容：
1. 基本游戏循环
2. 脏区域检测效果
3. 帧率统计
4. GIF动图序列播放

使用方法：
    python example_game.py [image_path_or_dir]

按 Ctrl+C 退出
"""

import sys
import time
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from gpu_ascii import GpuAscii, GameRenderer, get_terminal_size


def find_test_image():
    """查找测试图片"""
    extensions = [".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp"]
    script_dir = Path(__file__).parent
    search_dirs = [script_dir, script_dir.parent, Path.cwd()]
    
    for dir_path in search_dirs:
        if not dir_path.exists():
            continue
        for ext in extensions:
            for img in dir_path.glob(f"*{ext}"):
                return str(img)
    return None


def load_gif_frames(gif_dir: str) -> list:
    """
    加载GIF动图帧序列
    
    假设文件名格式: frame_XX_delay-Y.YYs.gif
    按帧序号排序，提取延迟时间
    """
    gif_path = Path(gif_dir)
    if not gif_path.exists():
        return []
    
    # 查找所有gif文件
    frames = []
    pattern = re.compile(r'frame_(\d+)_delay-([\d.]+)s\.gif')
    
    for file in gif_path.glob("*.gif"):
        match = pattern.match(file.name)
        if match:
            frame_num = int(match.group(1))
            delay = float(match.group(2))
            frames.append({
                'path': str(file),
                'frame': frame_num,
                'delay': delay,
            })
    
    # 按帧序号排序
    frames.sort(key=lambda x: x['frame'])
    return frames


def demo_basic(image_path: str):
    """基本游戏循环演示"""
    print("=== 基本游戏循环演示 ===")
    print("按 Ctrl+C 退出")
    time.sleep(2)
    
    gpu = GpuAscii()
    
    with GameRenderer(gpu) as renderer:
        frame_count = 0
        start_time = time.time()
        
        try:
            while True:
                info = renderer.update_to_terminal(image_path)
                frame_count += 1
                
        except KeyboardInterrupt:
            pass
        finally:
            elapsed = time.time() - start_time
            fps = frame_count / elapsed if elapsed > 0 else 0
            print(f"\n\n统计:")
            print(f"  总帧数: {frame_count}")
            print(f"  运行时间: {elapsed:.2f}秒")
            print(f"  平均帧率: {fps:.1f} FPS")


def demo_dirty_region(image_path: str):
    """脏区域检测演示"""
    print("=== 脏区域检测演示 ===")
    print("观察脏区域比例变化")
    print("按 Ctrl+C 退出")
    time.sleep(2)
    
    gpu = GpuAscii()
    
    with GameRenderer(gpu) as renderer:
        frame_count = 0
        total_dirty = 0
        total_cells = 0
        
        try:
            while True:
                info = renderer.update_to_terminal(image_path)
                frame_count += 1
                total_dirty += info.dirty_cells
                total_cells += info.total_cells
                
        except KeyboardInterrupt:
            pass
        finally:
            if frame_count > 0:
                avg_dirty = total_dirty / frame_count
                avg_cells = total_cells / frame_count
                dirty_ratio = (avg_dirty / avg_cells * 100) if avg_cells > 0 else 0
                print(f"\n\n脏区域统计:")
                print(f"  总帧数: {frame_count}")
                print(f"  平均脏区域: {avg_dirty:.0f} / {avg_cells:.0f}")
                print(f"  脏区域比例: {dirty_ratio:.1f}%")


def demo_gif_sequence(gif_dir: str):
    """GIF动图序列播放演示"""
    print("=== GIF动图序列播放 ===")
    print(f"加载目录: {gif_dir}")
    
    frames = load_gif_frames(gif_dir)
    
    if not frames:
        print("错误: 未找到符合格式的GIF帧文件")
        print("期望格式: frame_XX_delay-YYYs.gif")
        return
    
    print(f"找到 {len(frames)} 帧")
    print(f"帧延迟: {frames[0]['delay']}秒 ({1/frames[0]['delay']:.1f} FPS)")
    print()
    print("按 Ctrl+C 退出")
    time.sleep(2)
    
    gpu = GpuAscii()
    
    with GameRenderer(gpu) as renderer:
        frame_count = 0
        loop_count = 0
        start_time = time.time()
        total_dirty = 0
        total_cells = 0
        
        try:
            while True:
                # 循环播放
                for frame_info in frames:
                    frame_start = time.time()
                    
                    info = renderer.update_to_terminal(frame_info['path'])
                    frame_count += 1
                    total_dirty += info.dirty_cells
                    total_cells += info.total_cells
                    
                    # 精确控制帧延迟
                    elapsed = time.time() - frame_start
                    sleep_time = frame_info['delay'] - elapsed
                    if sleep_time > 0:
                        time.sleep(sleep_time)
                
                loop_count += 1
                
        except KeyboardInterrupt:
            pass
        finally:
            elapsed = time.time() - start_time
            fps = frame_count / elapsed if elapsed > 0 else 0
            avg_dirty = total_dirty / frame_count if frame_count > 0 else 0
            avg_cells = total_cells / frame_count if frame_count > 0 else 0
            dirty_ratio = (avg_dirty / avg_cells * 100) if avg_cells > 0 else 0
            
            print(f"\n\n播放统计:")
            print(f"  循环次数: {loop_count}")
            print(f"  总帧数: {frame_count}")
            print(f"  运行时间: {elapsed:.2f}秒")
            print(f"  平均帧率: {fps:.1f} FPS")
            print(f"  脏区域比例: {dirty_ratio:.1f}%")


def demo_gif_debug(gif_dir: str):
    """GIF动图逐帧调试模式"""
    print("=== GIF逐帧调试模式 ===")
    print(f"加载目录: {gif_dir}")
    
    frames = load_gif_frames(gif_dir)
    
    if not frames:
        print("错误: 未找到符合格式的GIF帧文件")
        return
    
    print(f"找到 {len(frames)} 帧")
    print()
    print("操作说明:")
    print("  按回车键 - 显示下一帧")
    print("  输入 r   - 重新开始")
    print("  输入 q   - 退出")
    print()
    input("按回车开始...")
    
    gpu = GpuAscii()
    frame_idx = 0
    
    with GameRenderer(gpu) as renderer:
        while frame_idx < len(frames):
            frame_info = frames[frame_idx]
            
            # 渲染当前帧
            info = renderer.update_to_terminal(frame_info['path'])
            
            # 显示帧信息（会在备用屏幕中显示，然后被下一帧覆盖）
            # 我们用stderr输出调试信息，避免干扰渲染
            print(f"Frame {frame_info['frame']}: dirty={info.dirty_cells}/{info.total_cells} grid={info.grid_width}x{info.grid_height}", file=sys.stderr)
            
            # 等待用户输入
            user_input = input()
            
            if user_input.strip().lower() == 'q':
                break
            elif user_input.strip().lower() == 'r':
                frame_idx = 0
                # 重新初始化渲染器
                renderer.cleanup()
                renderer.init()
                print("重新开始", file=sys.stderr)
            else:
                frame_idx += 1
    
    print(f"\n调试结束，共显示 {frame_idx} 帧")


def demo_multiple_images(image_dir: str):
    """多图像轮播演示"""
    print("=== 多图像轮播演示 ===")
    print("按 Ctrl+C 退出")
    time.sleep(2)
    
    # 查找目录中的所有图片
    extensions = [".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp"]
    images = []
    for ext in extensions:
        images.extend(Path(image_dir).glob(f"*{ext}"))
    
    if not images:
        print("未找到图片文件")
        return
    
    print(f"找到 {len(images)} 张图片")
    
    gpu = GpuAscii()
    
    with GameRenderer(gpu) as renderer:
        frame_count = 0
        start_time = time.time()
        
        try:
            while True:
                # 轮播图片
                img_path = str(images[frame_count % len(images)])
                info = renderer.update_to_terminal(img_path)
                frame_count += 1
                time.sleep(0.5)  # 每0.5秒切换一次
                
        except KeyboardInterrupt:
            pass
        finally:
            elapsed = time.time() - start_time
            print(f"\n\n统计:")
            print(f"  切换次数: {frame_count}")
            print(f"  运行时间: {elapsed:.2f}秒")


def main():
    """主函数"""
    # 检查命令行参数
    if len(sys.argv) > 1:
        input_path = sys.argv[1]
    else:
        # 默认查找test_gif目录
        script_dir = Path(__file__).parent
        test_gif_dir = script_dir / "test_gif"
        if test_gif_dir.exists():
            input_path = str(test_gif_dir)
        else:
            input_path = find_test_image()
    
    if not input_path:
        print("错误: 未找到测试图片或目录")
        print("用法: python example_game.py [image_path_or_dir]")
        sys.exit(1)
    
    # 判断是目录还是文件
    is_dir = Path(input_path).is_dir()
    
    print(f"输入: {input_path}")
    print()
    print("选择演示模式:")
    print("  1. 基本游戏循环")
    print("  2. 脏区域检测")
    if is_dir:
        print("  3. GIF动图序列播放 (推荐)")
        print("  4. 多图像轮播")
        print("  5. GIF逐帧调试模式")
    else:
        print("  3. 多图像轮播")
    print()
    
    choice = input("请选择: ").strip()
    
    if choice == "1":
        if is_dir:
            frames = load_gif_frames(input_path)
            if frames:
                demo_basic(frames[0]['path'])
            else:
                print("错误: 目录中未找到GIF帧文件")
        else:
            demo_basic(input_path)
    elif choice == "2":
        if is_dir:
            frames = load_gif_frames(input_path)
            if frames:
                demo_dirty_region(frames[0]['path'])
            else:
                print("错误: 目录中未找到GIF帧文件")
        else:
            demo_dirty_region(input_path)
    elif choice == "3":
        if is_dir:
            demo_gif_sequence(input_path)
        else:
            demo_multiple_images(str(Path(input_path).parent))
    elif choice == "4" and is_dir:
        demo_multiple_images(input_path)
    elif choice == "5" and is_dir:
        demo_gif_debug(input_path)
    else:
        print("无效选择，运行默认演示...")
        if is_dir:
            demo_gif_sequence(input_path)
        else:
            demo_basic(input_path)


if __name__ == "__main__":
    main()
