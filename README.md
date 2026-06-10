[中文](README_zh.md) | English

# GPU-ASCII

GPU-accelerated image-to-ASCII converter + terminal game engine

Uses wgpu compute shaders to process images in parallel on the GPU, mapping pixels to ASCII characters via the BT.709 perceptual luminance algorithm. Supports static image conversion and real-time game mode rendering, with a complete Python game engine framework.

## Features

- **GPU Acceleration** — wgpu compute shaders with sRGB gamma correction + BT.709 perceptual luminance
- **Color Output** — ColorShader outputs both character indices and RGB colors
- **Game Mode** — Alternate screen + dirty region detection for flicker-free dynamic refresh
- **Adaptive Terminal** — Auto-calculates optimal cell_size based on image and terminal dimensions, compensates for 2:1 character aspect ratio
- **Multiple Charsets** — 5 built-in presets, with custom support
- **Game Engine Framework** — Game loop, input system, scene stack, sprite animation
- **Cross-language** — C ABI FFI interface, Python ctypes zero-dependency calls

## Quick Start

### Build

```bash
# Requires Rust toolchain + Visual Studio Build Tools (MSVC)
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

# Quick conversion
text = image_to_ascii("image.png", fit_terminal=True)
print(text)

# Fine-grained control
gpu = GpuAscii()
result = gpu.convert_to_terminal("image.png")
print(result.text)
```

## Game Engine

### Game Loop

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

### Scene Management

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

### Sprite Animation

```python
from gpu_ascii import SpriteSheet, SpriteAnimator

sprite_sheet = SpriteSheet.from_gif_frames("test_gif/")
animator = SpriteAnimator(sprite_sheet, frame_rate=20.0, loop=True)

# In game loop
animator.update(delta_time)
frame = animator.get_current_frame()
renderer.update_to_terminal(frame.path)
```

## API

### Core Classes

| Class | Description |
|---|---|
| `GpuAscii` | GPU context, image-to-ASCII conversion |
| `GameRenderer` | Game renderer with dirty region detection |
| `GameLoop` | Frame timing, FPS control |
| `InputManager` | Keyboard input detection |
| `Scene` / `SceneManager` | Scene stack management |
| `SpriteSheet` / `SpriteAnimator` | Sprite frames and animation |

### GameRenderer Methods

| Method | Description |
|---|---|
| `init()` | Initialize (alternate screen) |
| `init_debug()` | Initialize (debug mode) |
| `update(path, cell_size)` | Render one frame from file |
| `update_to_terminal(path)` | Auto-fit terminal render |
| `update_from_memory(rgba, w, h)` | Render from memory data |
| `cleanup()` | Restore terminal state |

### Charsets

| Constant | Value |
|---|---|
| `DEFAULT_CHAR_RAMP` | `" .:-=+*#%@"` |
| `DENSE_CHAR_RAMP` | `" .:;+=xX$#@█"` |
| `MINIMAL_CHAR_RAMP` | `" ·░█"` |
| `BLOCK_CHAR_RAMP` | `" ░▒▓█"` |

## Examples

| File | Description |
|---|---|
| `python/example.py` | Basic usage |
| `python/example_game.py` | Game mode (GIF playback) |
| `python/example_engine.py` | Engine comprehensive example |
| `python/test_engine.py` | Functional tests |
| `python/debug_frames.py` | Frame-by-frame debug |

## Project Structure

```
gpu-ascii/
├── Cargo.toml
├── shaders/
│   ├── ascii.wgsl              # Character index shader
│   └── ascii_color.wgsl        # Character index + color shader
├── src/
│   ├── main.rs                 # CLI entry
│   ├── lib.rs                  # Library root module
│   ├── ffi.rs                  # C ABI FFI interface
│   ├── ascii/
│   │   ├── converter.rs        # GPU converter
│   │   ├── renderer.rs         # Static renderer
│   │   └── game_renderer.rs    # Game renderer
│   ├── cli/
│   │   ├── args.rs             # CLI argument definitions
│   │   └── mod.rs
│   └── gpu/
│       ├── context.rs          # GPU context
│       └── shader.rs           # Compute pipeline
└── python/
    ├── __init__.py
    ├── gpu_ascii.py            # Python bindings
    └── example*.py             # Example scripts
```

## Dependencies

### Rust

| Dependency | Purpose |
|---|---|
| wgpu 24.0 | GPU compute |
| image 0.25 | Image processing |
| crossterm 0.28 | Terminal control |
| clap 4.5 | CLI arguments |
| tokio 1.42 | Async runtime |

### Python

No third-party dependencies — calls the Rust dynamic library via ctypes.

## License

MIT
