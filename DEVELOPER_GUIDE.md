# GPU-ASCII 开发者文档

GPU 加速的图像转 ASCII 工具 + 终端游戏引擎框架。

底层使用 Rust + wgpu compute shader 并行处理图像，通过 C ABI FFI 导出动态库，
Python 端通过 ctypes 零依赖调用。

---

## 目录

- [环境要求](#环境要求)
- [构建](#构建)
- [快速开始](#快速开始)
- [Python API 参考](#python-api-参考)
  - [GpuAscii — 核心转换器](#gpuascii--核心转换器)
  - [GameRenderer — 游戏模式渲染器](#gamerenderer--游戏模式渲染器)
  - [GameLoop — 帧循环管理](#gameloop--帧循环管理)
  - [InputManager — 键盘输入](#inputmanager--键盘输入)
  - [RawKeyboard — Win32 原始键盘](#rawkeyboard--win32-原始键盘)
  - [Scene / SceneManager — 场景栈](#scene--scenemanager--场景栈)
  - [SpriteSheet / SpriteAnimator — 精灵动画](#spritesheet--spriteanimator--精灵动画)
- [示例说明](#示例说明)
- [项目结构](#项目结构)
- [注意事项](#注意事项)
- [故障排查](#故障排查)

---

## 环境要求

**Rust 端:**
- Rust toolchain (rustup)
- Visual Studio Build Tools (MSVC linker)，Windows 必须
- 支持 Vulkan / DX12 / Metal 的 GPU（wgpu 自动选择后端）

**Python 端:**
- Python >= 3.8
- 无第三方依赖（纯 ctypes 调用动态库）
- `PIL` / `Pillow` 仅平台跳跃游戏 (`game.py`) 需要

---

## 构建

```bash
# 在项目根目录
cargo build --release
```

产物路径:
- Windows: `target/release/gpu_ascii.dll`
- Linux:   `target/release/libgpu_ascii.so`
- macOS:   `target/release/libgpu_ascii.dylib`

Python 绑定会自动在以下路径搜索动态库:
1. `target/release/`
2. `target/debug/`
3. 运行时 `cwd/target/release/` 和 `cwd/target/debug/`

也可以手动指定:
```python
gpu = GpuAscii(lib_path="/path/to/gpu_ascii.dll")
```

---

## 快速开始

### 静态图像转换

```python
import sys
sys.path.insert(0, "python")   # 或者把 python/ 加入 PYTHONPATH

from gpu_ascii import GpuAscii, image_to_ascii

# 方式 1: 便捷函数（一行搞定）
text = image_to_ascii("photo.png", cell_size=8)
print(text)

# 方式 2: 自动适配终端大小
text = image_to_ascii("photo.png", fit_terminal=True)
print(text)

# 方式 3: 完整控制
gpu = GpuAscii()
result = gpu.convert(
    image_path="photo.png",
    cell_size=16,
    char_ramp=" .:;+=xX$#@█",
    use_color=False,
)
print(f"ASCII 尺寸: {result.width}x{result.height}")
print(result.text)
```

### 游戏模式（动态刷新）

```python
from gpu_ascii import GpuAscii, GameRenderer, GameLoop

gpu = GpuAscii()
renderer = GameRenderer(gpu)
game_loop = GameLoop(target_fps=30)

renderer.init()  # 进入备用屏幕，隐藏光标
try:
    while game_loop.begin_frame():
        renderer.update_to_terminal("frame.png")
        game_loop.end_frame()
finally:
    renderer.cleanup()  # 恢复终端
```

---

## Python API 参考

所有 Python API 位于 `python/gpu_ascii.py`，通过 `python/__init__.py` 统一导出。

### GpuAscii — 核心转换器

GPU 上下文，负责图像到 ASCII 的转换。

```python
class GpuAscii(lib_path: str | None = None)
```

| 方法 | 签名 | 说明 |
|------|------|------|
| `get_image_info` | `(image_path: str) -> (int, int)` | 返回图像 (width, height)，不进行转换 |
| `calc_cell_size` | `(img_w, img_h, term_w?, term_h?) -> int` | 根据图像和终端尺寸计算最优 cell_size |
| `convert` | `(image_path, cell_size=8, char_ramp=" .:-=+*#%@", use_color=False) -> AsciiResult` | 转换图像为 ASCII |
| `convert_to_terminal` | `(image_path, char_ramp, use_color, terminal_width?, terminal_height?, padding=1) -> AsciiResult` | 自动适配终端大小转换 |

**AsciiResult:**
```python
@dataclass
class AsciiResult:
    text: str      # ASCII 文本
    width: int     # 输出列数
    height: int    # 输出行数
```

**char_ramp 规则:** 字符串从左到右对应从暗到亮的像素亮度。空格 = 最暗（背景），最后一个字符 = 最亮。字符数量影响亮度分级精度。

内置参考字符集:
```
标准:  " .:-=+*#%@"
密集:  " .:;+=xX$#@█"
极简:  " ·░█"
方块:  " ░▒▓█"
```

---

### GameRenderer — 游戏模式渲染器

单页面动态渲染，支持脏区域检测（只重绘变化的字符格）。

```python
class GameRenderer(gpu: GpuAscii, char_ramp: str = " .:-=+*#%@")
```

支持 `with` 语句（上下文管理器）。

| 方法 | 签名 | 说明 |
|------|------|------|
| `init` | `()` | 进入备用屏幕（alternate screen），隐藏光标 |
| `init_debug` | `()` | 调试模式（不进入备用屏幕，可与 `input()` 配合） |
| `update` | `(image_path, cell_size=8) -> FrameInfo` | 渲染一帧，手动指定 cell_size |
| `update_to_terminal` | `(image_path, padding=1) -> FrameInfo` | 渲染一帧，自动适配终端 |
| `update_from_memory` | `(rgba_data: bytes, width, height, cell_size=8, char_ramp) -> FrameInfo` | 从内存 RGBA 数据渲染 |
| `get_frame_count` | `() -> int` | 已渲染帧数 |
| `set_terminal_height` | `(height: int)` | 限制输出行数，防止滚动 |
| `cleanup` | `()` | 恢复终端状态（显示光标，移动光标到内容下方） |

**FrameInfo:**
```python
@dataclass
class FrameInfo:
    dirty_cells: int   # 本帧变化的字符格数
    total_cells: int   # 总字符格数
    grid_width: int    # 网格列数
    grid_height: int   # 网格行数
```

**init() vs init_debug():**
- `init()` — 进入终端备用屏幕（类似 vim），游戏结束时 `cleanup()` 恢复。适合正式游戏。
- `init_debug()` — 不切换屏幕，输出留在主屏幕。适合开发调试，可以配合 `input()` 逐帧暂停。

---

### GameLoop — 帧循环管理

控制帧率、计算 delta_time、统计 FPS。

```python
class GameLoop(target_fps: int = 30)
```

| 属性/方法 | 类型 | 说明 |
|-----------|------|------|
| `begin_frame()` | `-> bool` | 帧开始，返回 True（可扩展为退出条件） |
| `end_frame()` | `()` | 帧结束，自动 sleep 补齐到目标帧率 |
| `delta_time` | `float` | 当前帧与上一帧的时间差（秒） |
| `fps` | `float` | 实时 FPS（每秒更新一次） |
| `frame_count` | `int` | 累计帧数 |
| `stop()` | `()` | 停止循环 |
| `reset()` | `()` | 重置所有状态 |

**典型用法:**
```python
game_loop = GameLoop(target_fps=30)
while game_loop.begin_frame():
    dt = game_loop.delta_time
    # 更新逻辑...
    # 渲染...
    game_loop.end_frame()
```

---

### InputManager — 键盘输入

基于 `msvcrt` 的键盘输入检测（Windows）。

```python
class InputManager()
```

| 方法 | 说明 |
|------|------|
| `update()` | 每帧调用，刷新按键状态 |
| `is_key_pressed(key: str) -> bool` | 按键是否处于按下状态 |
| `is_key_just_pressed(key: str) -> bool` | 本帧是否刚按下 |
| `is_key_just_released(key: str) -> bool` | 本帧是否刚松开 |
| `get_mouse_position() -> (int, int)` | 鼠标坐标（预留，当前返回 0,0） |
| `clear()` | 清除所有按键状态 |

**注意:** `InputManager` 基于 `msvcrt.kbhit()` / `msvcrt.getch()`，仅支持 Windows，且不支持方向键等特殊键。如需方向键支持，请使用 `RawKeyboard`。

---

### RawKeyboard — Win32 原始键盘

使用 `GetAsyncKeyState` 轮询硬件按键状态，支持方向键、空格等所有键。

```python
from rawkb import RawKeyboard

kb = RawKeyboard()
```

| 方法 | 说明 |
|------|------|
| `poll()` | 每帧调用，刷新按键状态 |
| `is_down(key: str) -> bool` | 当前是否按住 |
| `just_pressed(key: str) -> bool` | 本帧是否刚按下 |
| `just_released(key: str) -> bool` | 本帧是否刚松开 |

**支持的按键名:**
- 字母: `'a'` ~ `'z'`（不区分大小写）
- 数字: `'0'` ~ `'9'`
- 方向键: `'left'`, `'right'`, `'up'`, `'down'`
- 功能键: `'space'`, `'enter'`, `'esc'`, `'tab'`, `'backspace'`
- 修饰键: `'shift'`, `'ctrl'`, `'alt'`
- F键: `'f1'` ~ `'f12'`

**仅 Windows 可用**，非 Windows 平台所有方法返回 False。

**与 InputManager 的区别:**

| 特性 | InputManager | RawKeyboard |
|------|-------------|-------------|
| 底层 | msvcrt getch 缓冲区 | GetAsyncKeyState 硬件轮询 |
| 方向键 | 不支持 | 支持 |
| 多键同时按下 | 不支持 | 支持 |
| 非 Windows | 有限支持 | 不支持 |
| 依赖 | gpu_ascii.py 内置 | 独立模块 rawkb.py |

---

### Scene / SceneManager — 场景栈

场景管理器，支持 push/pop/switch 操作。

```python
class Scene(ABC):
    name: str
    def on_enter(self): ...      # 进入场景时
    def on_exit(self): ...       # 离开场景时
    def on_pause(self): ...      # 被压入栈下方时
    def on_resume(self): ...     # 从栈下方恢复时
    def update(self, delta_time: float): ...  # 必须实现
    def render(self, renderer): ...           # 必须实现
    def set_data(key, value): ...
    def get_data(key, default=None): ...
```

```python
class SceneManager()
```

| 方法 | 说明 |
|------|------|
| `push_scene(scene)` | 压入新场景（当前场景 on_pause） |
| `pop_scene()` | 弹出顶部场景（当前 on_exit，下方 on_resume） |
| `switch_scene(scene)` | 替换顶部场景（当前 on_exit，新场景 on_enter） |
| `clear_scenes()` | 弹出所有场景 |
| `update(delta_time)` | 更新当前（顶部）场景 |
| `render(renderer)` | 渲染当前（顶部）场景 |
| `current_scene -> Scene | None` | 当前场景 |
| `scene_count -> int` | 场景栈深度 |

**自定义场景示例:**
```python
class MenuScene(Scene):
    def __init__(self):
        super().__init__("menu")

    def update(self, delta_time):
        pass

    def render(self, renderer):
        renderer.update_to_terminal("menu_bg.png")
```

---

### SpriteSheet / SpriteAnimator — 精灵动画

精灵表和帧动画控制器。

```python
class SpriteSheet(frames: list[SpriteFrame], gpu: GpuAscii | None = None)
```

| 类方法 | 说明 |
|--------|------|
| `SpriteSheet.from_gif_frames(gif_dir, pattern)` | 从 GIF 帧目录加载（文件名格式: `frame_XX_delay-Y.YYs.gif`） |
| `SpriteSheet.from_images(image_paths)` | 从图片路径列表加载 |

| 方法/属性 | 说明 |
|-----------|------|
| `frame_count -> int` | 帧数 |
| `get_frame(index) -> SpriteFrame` | 获取帧（支持循环索引） |
| `get_ascii_result(index, cell_size, char_ramp) -> AsciiResult` | 获取转换结果（带缓存） |

```python
class SpriteAnimator(sprite_sheet, frame_rate=10.0, loop=True)
```

| 方法/属性 | 说明 |
|-----------|------|
| `update(delta_time)` | 推进动画时间 |
| `get_current_frame() -> SpriteFrame` | 当前帧 |
| `play()` / `pause()` / `stop()` / `reset()` | 播放控制 |
| `current_frame_index -> int` | 当前帧索引 |
| `is_playing -> bool` | 是否播放中 |
| `is_finished -> bool` | 是否播放完毕（非循环模式） |

**SpriteFrame:**
```python
@dataclass
class SpriteFrame:
    path: str              # 帧图片路径
    frame_index: int       # 帧序号
    ascii_result: AsciiResult | None = None  # 缓存的转换结果
```

---

## 示例说明

| 文件 | 说明 | 运行方式 |
|------|------|----------|
| `python/example.py` | 静态图像转换（基础/高级/不同字符集/输出到文件） | `python python/example.py` |
| `python/example_game.py` | 游戏模式演示（基本循环/脏区域检测/GIF播放/轮播/逐帧调试） | `python python/example_game.py [图片或目录]` |
| `python/example_engine.py` | 引擎综合示例（场景系统 + 精灵动画 + 帧循环） | `python python/example_engine.py` |
| `python/test_engine.py` | 功能测试（GameLoop/InputManager/SpriteSheet/GameRenderer） | `python python/test_engine.py` |
| `python/debug_frames.py` | GIF 逐帧调试（按回车推进一帧） | `python python/debug_frames.py` |
| `python/games/platformer/game.py` | 完整平台跳跃游戏（物理/碰撞/关卡生成/金币/生命系统） | `python python/games/platformer/game.py` |

所有示例通过 `sys.path.insert` 自动定位 `gpu_ascii` 模块，无需安装。

---

## 项目结构

```
gpu-ascii/
├── Cargo.toml                # Rust 项目配置
├── pyproject.toml            # Python 包配置
├── README.md                 # 英文 README
├── DEVELOPER_GUIDE.md        # 本文档
├── shaders/
│   ├── ascii.wgsl            # 字符索引计算着色器
│   └── ascii_color.wgsl      # 字符索引 + 颜色着色器
├── src/
│   ├── main.rs               # CLI 入口
│   ├── lib.rs                # 库模块声明
│   ├── ffi.rs                # C ABI FFI 导出函数
│   ├── ascii/
│   │   ├── converter.rs      # GPU 转换器（AsciiConverter）
│   │   ├── renderer.rs       # 静态渲染器（终端输出）
│   │   └── game_renderer.rs  # 游戏渲染器（脏区域检测）
│   ├── cli/
│   │   ├── args.rs           # CLI 参数定义（clap）
│   │   └── mod.rs
│   └── gpu/
│       ├── context.rs        # wgpu 设备/队列管理
│       ├── shader.rs         # Compute pipeline 构建
│       └── mod.rs
└── python/
    ├── __init__.py           # 包入口，导出所有公共 API
    ├── gpu_ascii.py          # 核心模块（GpuAscii/GameRenderer/GameLoop/...）
    ├── rawkb.py              # Win32 原始键盘输入
    ├── example*.py           # 示例脚本
    ├── test_engine.py        # 功能测试
    ├── debug_frames.py       # 逐帧调试
    ├── games/
    │   └── platformer/
    │       └── game.py       # 平台跳跃游戏
    ├── assets/               # 游戏素材（tiles/player/backgrounds）
    ├── test_gif/             # 测试用 GIF 帧序列
    └── examples/             # 示例副本（冗余，待清理）
```

---

## 注意事项

### 1. 动态库必须先编译

Python 绑定依赖 Rust 编译产物 (`gpu_ascii.dll` / `libgpu_ascii.so`)。
运行任何 Python 脚本前必须先:
```bash
cargo build --release
```

### 2. RawKeyboard 仅 Windows

`rawkb.py` 使用 Win32 API `GetAsyncKeyState`，非 Windows 平台无法使用。
跨平台场景请用 `InputManager`（基于 `msvcrt`，功能较弱）。

### 3. GameRenderer 的 init() vs init_debug()

- `init()` 切换到备用屏幕，终端内容会被清空，`cleanup()` 后恢复。
- `init_debug()` 不切换屏幕，输出留在主屏幕，适合用 `input()` 交互调试。
- 两者**不能混用**，一个 renderer 实例只能 init 一次（除非 cleanup 后重新 init）。

### 4. 资源释放

`GpuAscii` 和 `GameRenderer` 持有 Rust 侧的堆分配句柄。
- 推荐用 `with` 语句管理 `GameRenderer`。
- `GpuAscii` 会在 `__del__` 中自动释放，但建议显式管理或保持单例。
- **不要**在 `GameRenderer` 的 `__del__` 之前调用 `GpuAscii` 的 `__del__`，否则会 UAF。

### 5. cell_size 含义

`cell_size` 表示每个 ASCII 字符对应原图的像素块大小。
- 值越小 → 输出越大越精细
- 值越大 → 输出越小越粗糙
- `calc_cell_size()` 会根据图像和终端尺寸自动计算最优值（考虑字符 2:1 高宽比）

### 6. 线程安全

所有 API 均非线程安全。Rust 侧 wgpu 上下文绑定到创建线程。
如果需要多线程，每个线程应创建独立的 `GpuAscii` 实例。

### 7. game.py 额外依赖

平台跳跃游戏 (`python/games/platformer/game.py`) 需要:
- `Pillow`（PIL）— 图像合成
- `rawkb.py` — 键盘输入（仅 Windows）

安装 Pillow:
```bash
pip install Pillow
```

### 8. GIF 帧文件命名

`SpriteSheet.from_gif_frames()` 和部分示例期望 GIF 帧文件名格式:
```
frame_00_delay-0.05s.gif
frame_01_delay-0.05s.gif
...
```
正则: `frame_(\d+)_delay-([\d.]+)s\.gif`

---

## 故障排查

**`FileNotFoundError: Cannot find gpu_ascii.dll`**
→ 未编译 Rust 库，运行 `cargo build --release`。

**`RuntimeError: Failed to initialize GPU context`**
→ GPU 不支持或驱动问题。确认有 Vulkan/DX12/Metal 支持。
→ 尝试设置环境变量 `WGPU_BACKEND=vulkan` 或 `WGPU_BACKEND=dx12`。

**`ImportError: No module named 'gpu_ascii'`**
→ 未将 `python/` 目录加入路径。在脚本中添加:
```python
import sys
sys.path.insert(0, "python")
```
或设置环境变量 `PYTHONPATH=python`。

**`AttributeError: module 'msvcrt' has no attribute 'kbhit'`**
→ 非 Windows 平台。`InputManager` 和 `RawKeyboard` 仅支持 Windows。

**终端输出闪烁**
→ 使用 `GameRenderer`（脏区域检测），不要每帧打印完整文本。
→ 确保调用 `init()` 而非 `init_debug()`（备用屏幕无闪烁）。

**ASCII 输出被截断**
→ `GameCanvas._to_ascii()` 会按 `max_rows` / `max_cols` 截断。
→ 检查终端窗口大小，或调整 `CELL_SIZE`。
