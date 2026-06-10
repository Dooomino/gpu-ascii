"""
GPU ASCII 使用示例
"""

import os
import sys
from pathlib import Path

# 添加当前目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from gpu_ascii import GpuAscii, image_to_ascii


def find_test_image():
    """查找测试图片"""
    # 常见图片格式
    extensions = [".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp"]
    
    # 搜索路径
    script_dir = Path(__file__).parent if '__file__' in dir() else Path.cwd()
    search_dirs = [
        script_dir,
        Path.cwd(),
        script_dir.parent,
        Path(r"D:\Projects\CLI Engine\gpu-ascii\python"),
    ]
    
    for dir_path in search_dirs:
        if not dir_path.exists():
            continue
        for ext in extensions:
            for img in dir_path.glob(f"*{ext}"):
                return str(img)
    
    return None


def example_basic(image_path: str):
    """基础用法"""
    print(f"=== 基础用法 ===")
    print(f"输入图片: {image_path}")
    
    try:
        # 使用便捷函数
        ascii_art = image_to_ascii(image_path, cell_size=8)
        print(ascii_art)
    except Exception as e:
        print(f"错误: {e}")


def example_advanced(image_path: str):
    """高级用法"""
    print(f"\n=== 高级用法 ===")
    
    try:
        # 创建实例
        gpu = GpuAscii()
        
        # 自定义字符集
        result = gpu.convert(
            image_path=image_path,
            cell_size=16,
            char_ramp=" .:;+=xX$#@█",  # 密集字符集
        )
        
        print(f"尺寸: {result.width}x{result.height}")
        print(result.text)
    except Exception as e:
        print(f"错误: {e}")


def example_different_ramps(image_path: str):
    """不同字符集效果"""
    print(f"\n=== 不同字符集 ===")
    
    try:
        gpu = GpuAscii()
        
        ramps = {
            "标准": " .:-=+*#%@",
            "密集": " .:;+=xX$#@█",
            "极简": " ·░█",
            "方块": " ░▒▓█",
        }
        
        for name, ramp in ramps.items():
            print(f"\n{name}:")
            result = gpu.convert(image_path, cell_size=8, char_ramp=ramp)
            print(result.text[:200])  # 只显示前200字符
    except Exception as e:
        print(f"错误: {e}")


def example_to_file(image_path: str):
    """输出到文件"""
    print(f"\n=== 输出到文件 ===")
    
    try:
        result = image_to_ascii(image_path, cell_size=8)
        
        output_path = Path(__file__).parent / "output.txt"
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(result)
        
        print(f"已保存到: {output_path}")
    except Exception as e:
        print(f"错误: {e}")


if __name__ == "__main__":
    # 查找测试图片
    image_path = find_test_image()
    
    if image_path is None:
        print("错误: 未找到测试图片")
        print("请在以下目录放置图片文件:")
        print(f"  - {Path(__file__).parent}")
        print(f"  - {Path.cwd()}")
        print(f"支持格式: jpg, jpeg, png, bmp, gif, webp")
        sys.exit(1)
    
    print(f"找到测试图片: {image_path}\n")
    
    # 请确保先编译Rust库:
    # cargo build --release
    
    example_basic(image_path)
    example_advanced(image_path)
    example_different_ramps(image_path)
    example_to_file(image_path)
