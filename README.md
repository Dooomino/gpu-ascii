# GPU-ASCII

GPU 加速的图像转 ASCII 工具 + 终端游戏引擎

## 简介

GPU-ASCII 使用 wgpu 计算着色器在 GPU 上并行处理图像，将像素亮度映射为 ASCII 字符。支持静态图像转换和实时游戏模式渲染，提供完整的 Python 游戏引擎框架。

## 特性

- **GPU 加速** — wgpu 计算着色器并行处理，BT.709 感知亮度计算
- **彩色输出** — 同时输出字符索引和 RGB 颜色
- **游戏模式** — 备用屏幕 + 脏区域检测，无闪烁动态刷新
- **自适应终端** — 根据图像和终端大小自动计算最优 cell_size
- **多种字符集** — 预设 5 种字符集，支持自定义
- **游戏引擎框架** — 游戏循环、输入系统、场景管理、精灵动画
- **跨语言调用** — C ABI FFI 接口，支持 Python ctypes

## 快速开始

### 构建

```bash
# 需要 Rust 工具链和 Visual Studio Build Tools
cargo build --release
```

### CLI 使用

```bash
# 基本转换
gpu-ascii image.png

# 指定参数
gpu-ascii image.png --cell-size 4 --ramp dense --color

# 输出到文件
gpu-ascii image.png -o output.txt
```

### Python 使用

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

### 基本游戏循环

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
scene_mgr.update(delta_time)
scene_mgr.render(renderer)
```

### 精灵动画

```python
from gpu_ascii import SpriteSheet, SpriteAnimator

# 从 GIF 帧序列加载
sprite_sheet = SpriteSheet.from_gif_frames("test_gif/")
animator = SpriteAnimator(sprite_sheet, frame_rate=20.0, loop=True)

# 游戏循环中
animator.update(delta_time)
frame = animator.get_current_frame()
renderer.update_to_terminal(frame.path)
```

## API 参考

### 核心类

| 类 | 说明 |
|---|---|
| `GpuAscii` | GPU 上下文管理，图像转 ASCII |
| `GameRenderer` | 游戏模式渲染器，支持动态刷新 |
| `GameLoop` | 帧时间管理和 FPS 控制 |
| `InputManager` | 键盘输入检测 |
| `SceneManager` | 场景栈管理 |
| `SpriteSheet` | 精灵帧管理 |
| `SpriteAnimator` | 帧动画播放器 |

### 数据类

| 类 | 说明 |
|---|---|
| `AsciiResult` | 转换结果（text, width, height） |
| `FrameInfo` | 帧信息（dirty_cells, total_cells, grid_width, grid_height） |
| `SpriteFrame` | 精灵帧（path, frame_index） |
| `Scene` | 场景抽象基类 |

### 字符集常量

| 常量 | 值 |
|---|---|
| `DEFAULT_CHAR_RAMP` | `" .:-=+*#%@"` |
| `DENSE_CHAR_RAMP` | `" .:;+=xX$#@█"` |
| `MINIMAL_CHAR_RAMP` | `" ·░█"` |
| `BLOCK_CHAR_RAMP` | `" ░▒▓█"` |

## 项目结构

```
gpu-ascii/
├── Cargo.toml              # Rust 项目配置
├── shaders/
│   ├── ascii.wgsl          # 字符索引着色器
│   └── ascii_color.wgsl    # 字符索引+颜色着色器
├── src/
│   ├── main.rs             # CLI 入口
│   ├── lib.rs              # 库根模块
│   ├── ffi.rs              # C ABI FFI 接口
│   ├── ascii/
│   │   ├── converter.rs    # GPU 转换器
│   │   ├── renderer.rs     # 静态渲染器
│   │   └── game_renderer.rs # 游戏渲染器
│   └── gpu/
│       ├── context.rs      # GPU 上下文
│       └── shader.rs       # 计算管线
└── python/
    ├── gpu_ascii.py        # Python 绑定（全部类定义）
    ├── example.py          # 基础示例
    ├── example_game.py     # 游戏模式示例
    └── example_engine.py   # 引擎综合示例
```

## 技术栈

| 组件 | 技术 |
|---|---|
| GPU 计算 | wgpu + WGSL |
| 图像处理 | image crate |
| 终端控制 | crossterm |
| CLI | clap |
| Python 绑定 | ctypes + C ABI |

## 许可证

MIT
