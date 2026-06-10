"""
逐帧调试脚本 - 简化版
"""

import sys
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from gpu_ascii import GpuAscii, GameRenderer

gif_dir = Path(__file__).parent / "test_gif"

# 加载帧
frames = []
pattern = re.compile(r'frame_(\d+)_delay-([\d.]+)s\.gif')
for file in gif_dir.glob("*.gif"):
    match = pattern.match(file.name)
    if match:
        frame_num = int(match.group(1))
        frames.append({'path': str(file), 'frame': frame_num})

frames.sort(key=lambda x: x['frame'])

print(f"找到 {len(frames)} 帧")
print("按回车显示下一帧，输入q退出")
print()

gpu = GpuAscii()
renderer = GameRenderer(gpu)
renderer.init_debug()  # 不使用备用屏幕

try:
    for i, frame in enumerate(frames):
        # 使用update_to_terminal自动适配终端大小
        info = renderer.update_to_terminal(frame['path'])
        # 输出到stderr，不干扰渲染
        sys.stderr.write(f"[{i+1}/{len(frames)}] Frame {frame['frame']}: dirty={info.dirty_cells}/{info.total_cells} grid={info.grid_width}x{info.grid_height}\n")
        sys.stderr.flush()
        
        user = input()
        if user.strip().lower() == 'q':
            break
finally:
    renderer.cleanup()
    print("调试结束")
