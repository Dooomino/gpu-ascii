English | [中文](README_zh.md)

# GPU-ASCII

GPU 加速的图像转 ASCII 工具 + 终端游戏引擎

使用 wgpu 计算着色器在 GPU 上并行处理图像，通过 BT.709 感知亮度算法将像素映射为 ASCII 字符。支持静态图像转换和实时游戏模式渲染，提供完整的 Python 游戏引擎框架。

## 特性

- **GPU 加速** — wgpu 计算着色器并行处理，sRGB gamma 校正 + BT.709 感知亮度
- **彩色输出** — ColorShader 同时输出字符索引和 RGB 颜色
- **游戏模式** — 备用屏幕 + 脏区域检测，无闪烁动态刷新
- **自适应终端** — 根据图像和终端大小自动计算最优 cell_size，补偿字符 2:1 高宽比
- **多种字符集** — 预设 5 种字符集，支持自定义
- **游戏引擎框架** — 游戏循环、输入系统、场景栈、精灵动画
- **跨语言调用** — C ABI FFI 接口，Python ctypes 零依赖调用

## 快速开始

### 构建

```bash
# 需要 Rust 工具链 + Visual Studio Build Tools (MSVC)
cargo build --release
```

### CLI

```bash
gpu-ascii image.png
gpu-ascii image.png --cell-size 4 --ramp dense --color
gpu-ascii image.png -o output.txt
```

### Python

```python
from gpu_ascii import GpuAscii, image_to_ascii

# 快速转换
text = image_to_ascii("image.png", fit_terminal=True)
print(text)

# 详细控制
gpu = GpuAscii()
result = gpu.convert_to_terminal("image.png")
print(result.text)
```

## 游戏引擎

### 游戏循环

```python
from gpu_ascii import GpuAscii, GameRenderer, GameLoop, InputManager

gpu = GpuAscii()
renderer = GameRenderer(gpu)
game_loop = GameLoop(target_fps=30)
input_mgr = InputManager()

renderer.init_debug()
while game_loop.begin_frame():
    input_mgr.update()
    if input_mgr.is_key_pressed('q'):
        break
    renderer.update_to_terminal("frame.png")
    game_loop.end_frame()
renderer.cleanup()
```

### 场景管理

```python
from gpu_ascii import Scene, SceneManager

class GameScene(Scene):
    def update(self, delta_time):
        pass
    
    def render(self, renderer):
        renderer.update_to_terminal("game.png")

scene_mgr = SceneManager()
scene_mgr.push_scene(GameScene())
```

### 精灵动画

```python
from gpu_ascii import SpriteSheet, SpriteAnimator

sprite_sheet = SpriteSheet.from_gif_frames("test_gif/")
animator = SpriteAnimator(sprite_sheet, frame_rate=20.0, loop=True)

# 游戏循环中
animator.update(delta_time)
frame = animator.get_current_frame()
renderer.update_to_terminal(frame.path)
```

## API

### 核心类

| 类 | 说明 |
|---|---|
| `GpuAscii` | GPU 上下文，图像转 ASCII |
| `GameRenderer` | 游戏渲染器，脏区域检测 |
| `GameLoop` | 帧时间管理，FPS 控制 |
| `InputManager` | 键盘输入检测 |
| `Scene` / `SceneManager` | 场景栈管理 |
| `SpriteSheet` / `SpriteAnimator` | 精灵帧和动画 |

### GameRenderer 方法

| 方法 | 说明 |
|---|---|
| `init()` | 初始化（备用屏幕） |
| `init_debug()` | 初始化（调试模式） |
| `update(path, cell_size)` | 从文件渲染一帧 |
| `update_to_terminal(path)` | 自动适配终端渲染 |
| `update_from_memory(rgba, w, h)` | 从内存数据渲染 |
| `cleanup()` | 恢复终端状态 |

### 字符集

| 常量 | 值 |
|---|---|
| `DEFAULT_CHAR_RAMP` | `" .:-=+*#%@"` |
| `DENSE_CHAR_RAMP` | `" .:;+=xX$#@█"` |
| `MINIMAL_CHAR_RAMP` | `" ·░█"` |
| `BLOCK_CHAR_RAMP` | `" ░▒▓█"` |

## 示例

| 文件 | 说明 |
|---|---|
| `python/example.py` | 基础使用 |
| `python/example_game.py` | 游戏模式（GIF 播放） |
| `python/example_engine.py` | 引擎综合示例 |
| `python/test_engine.py` | 功能测试 |
| `python/debug_frames.py` | 逐帧调试 |

## 项目结构

```
gpu-ascii/
├── Cargo.toml
├── shaders/
│   ├── ascii.wgsl              # 字符索引着色器
│   └── ascii_color.wgsl        # 字符索引+颜色着色器
├── src/
│   ├── main.rs                 # CLI 入口
│   ├── lib.rs                  # 库根模块
│   ├── ffi.rs                  # C ABI FFI 接口
│   ├── ascii/
│   │   ├── converter.rs        # GPU 转换器
│   │   ├── renderer.rs         # 静态渲染器
│   │   └── game_renderer.rs    # 游戏渲染器
│   ├── cli/
│   │   ├── args.rs             # CLI 参数定义
│   │   └── mod.rs
│   └── gpu/
│       ├── context.rs          # GPU 上下文
│       └── shader.rs           # 计算管线
└── python/
    ├── __init__.py
    ├── gpu_ascii.py            # Python 绑定
    └── example*.py             # 示例脚本
```

## 依赖

### Rust

| 依赖 | 用途 |
|---|---|
| wgpu 24.0 | GPU 计算 |
| image 0.25 | 图像处理 |
| crossterm 0.28 | 终端控制 |
| clap 4.5 | CLI 参数 |
| tokio 1.42 | 异步运行时 |

### Python

无第三方依赖，通过 ctypes 调用 Rust 动态库。

## 许可证

MIT
