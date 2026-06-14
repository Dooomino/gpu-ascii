"""
平台跳跃游戏 - GPU-ASCII 引擎
==============================

操作说明:
  A/D 或 左/右箭头  - 移动
  W 或 空格         - 跳跃
  Q                - 退出

特性:
  - 重力物理引擎
  - 碰撞检测
  - 金币收集
  - 生命系统
  - 动态关卡生成
  - ASCII 渲染输出

运行:
  python python/games/platformer/game.py
"""

import sys
import os
import time
import math
import random
import shutil
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict
from enum import Enum

# 确保能导入 gpu_ascii
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from gpu_ascii import (
    GpuAscii, GameRenderer, GameLoop,
    Scene, SceneManager, SpriteSheet, SpriteAnimator,
    get_terminal_size, AsciiResult
)
from rawkb import RawKeyboard


def measure_terminal_size() -> Tuple[int, int]:
    """
    测量终端大小，优先使用系统API，失败时使用shutil
    Returns:
        (width, height) 终端列数和行数
    """
    # 方法1: 使用gpu_ascii的get_terminal_size
    try:
        tw, th = get_terminal_size()
        if tw > 0 and th > 0:
            return tw, th
    except:
        pass
    
    # 方法2: 使用shutil
    try:
        size = shutil.get_terminal_size()
        if size.columns > 0 and size.lines > 0:
            return size.columns, size.lines
    except:
        pass
    
    # 方法3: 默认值
    return 80, 24


# ============================================================
#  常量
# ============================================================

ASSETS = Path(__file__).parent.parent.parent / "assets"
PLAYER_FRAMES = ASSETS / "player"
TILES = ASSETS / "tiles"
BACKGROUNDS = ASSETS / "backgrounds"

# 物理常量
GRAVITY = 980.0        # 像素/秒²
JUMP_VELOCITY = -420.0 # 像素/秒 (向上为负)
MOVE_SPEED = 200.0     # 像素/秒
MAX_FALL_SPEED = 600.0 # 最大下落速度

# 游戏参数
CELL_SIZE = 2           # ASCII 字符单元格大小 (更小=更多细节)
PLAYER_W = 40           # 角色宽(像素)
PLAYER_H = 40           # 角色高(像素)
COIN_SIZE = 16
PLATFORM_H = 16

STARTING_LIVES = 3

# 世界坐标系 (Y轴向下为正，与PIL一致)
WORLD_GROUND_Y = 140   # 地面Y坐标 (适配画布高度)
WORLD_WIDTH = 6000     # 关卡总宽(像素)


# ============================================================
#  数据类型
# ============================================================

class TileType(Enum):
    GRASS = "grass"
    STONE = "stone"
    SPIKE = "spike"
    COIN = "coin"
    FLAG = "flag"


@dataclass
class Vec2:
    x: float = 0.0
    y: float = 0.0


@dataclass
class AABB:
    """轴对齐包围盒"""
    x: float
    y: float
    w: float
    h: float

    def overlaps(self, other: 'AABB') -> bool:
        return (self.x < other.x + other.w and
                self.x + self.w > other.x and
                self.y < other.y + other.h and
                self.y + self.h > other.y)


@dataclass
class Platform:
    x: float
    y: float
    width: float
    tile_type: TileType = TileType.GRASS

    @property
    def aabb(self) -> AABB:
        return AABB(self.x, self.y, self.width, PLATFORM_H)


@dataclass
class Coin:
    x: float
    y: float
    collected: bool = False
    anim_offset: float = 0.0

    @property
    def aabb(self) -> AABB:
        return AABB(self.x, self.y, COIN_SIZE, COIN_SIZE)


@dataclass
class Player:
    pos: Vec2 = field(default_factory=lambda: Vec2(100, WORLD_GROUND_Y - PLAYER_H))
    vel: Vec2 = field(default_factory=lambda: Vec2(0, 0))
    on_ground: bool = False
    facing_right: bool = True
    lives: int = STARTING_LIVES
    score: int = 0
    invincible_timer: float = 0.0  # 受伤无敌时间
    dead: bool = False
    win: bool = False

    @property
    def aabb(self) -> AABB:
        return AABB(self.pos.x, self.pos.y, PLAYER_W, PLAYER_H)


# ============================================================
#  关卡生成
# ============================================================

def generate_level(length: int = 200) -> Tuple[List[Platform], List[Coin], Vec2]:
    """
    程序化生成关卡

    Args:
        length: 关卡长度(格子数)

    Returns:
        (platforms, coins, flag_position)
    """
    platforms: List[Platform] = []
    coins: List[Coin] = []

    # 地面平台 (Y轴向下为正)
    ground_y = WORLD_GROUND_Y
    x = 0
    while x < WORLD_WIDTH:
        seg_len = random.randint(3, 8) * 40
        gap = random.randint(1, 3) * 40

        platforms.append(Platform(x, ground_y, seg_len, TileType.GRASS))

        # 在平台上方放金币
        if random.random() < 0.4:
            cx = x + random.randint(1, max(1, int(seg_len / 40) - 1)) * 40
            coins.append(Coin(cx, ground_y - 50))

        x += seg_len + gap

    # 浮空平台
    for i in range(length // 3):
        px = random.randint(200, WORLD_WIDTH - 200)
        py = ground_y - random.randint(60, 200)
        pw = random.randint(2, 5) * 40
        tile = random.choice([TileType.GRASS, TileType.STONE])
        platforms.append(Platform(px, py, pw, tile))

        # 浮空平台上放金币
        if random.random() < 0.6:
            coins.append(Coin(px + pw // 2, py - 40))

    # 阶梯平台
    stair_x = random.randint(300, WORLD_WIDTH // 2)
    stair_y = ground_y - 40
    for s in range(5):
        platforms.append(Platform(stair_x + s * 60, stair_y - s * 50, 80, TileType.STONE))
        if random.random() < 0.5:
            coins.append(Coin(stair_x + s * 60 + 30, stair_y - s * 50 - 40))

    # 尖刺陷阱
    spike_platforms = [p for p in platforms if p.tile_type == TileType.GRASS and p.width >= 120]
    for sp in random.sample(spike_platforms, min(5, len(spike_platforms))):
        sx = sp.x + random.randint(1, max(1, int(sp.width / 40) - 1)) * 40
        platforms.append(Platform(sx, sp.y - PLATFORM_H + 4, 40, TileType.SPIKE))

    # 终点旗帜
    flag_x = WORLD_WIDTH - 100
    flag_pos = Vec2(flag_x, ground_y - 48)

    return platforms, coins, flag_pos


# ============================================================
#  物理 & 碰撞
# ============================================================

def update_player(player: Player, platforms: List[Platform],
                  coins: List[Coin], flag_pos: Vec2,
                  dt: float, kb: RawKeyboard) -> None:
    """更新玩家物理和碰撞"""

    if player.dead or player.win:
        return

    # 无敌时间
    if player.invincible_timer > 0:
        player.invincible_timer -= dt

    # 水平移动
    dx = 0.0
    if kb.is_down('a') or kb.is_down('left'):
        dx -= 1
        player.facing_right = False
    if kb.is_down('d') or kb.is_down('right'):
        dx += 1
        player.facing_right = True

    player.vel.x = dx * MOVE_SPEED

    # 跳跃
    if kb.is_down('w') or kb.is_down('up') or kb.is_down('space'):
        if player.on_ground:
            player.vel.y = JUMP_VELOCITY
            player.on_ground = False

    # 重力
    player.vel.y += GRAVITY * dt
    if player.vel.y > MAX_FALL_SPEED:
        player.vel.y = MAX_FALL_SPEED

    # 水平移动 + 碰撞
    player.pos.x += player.vel.x * dt
    player_aabb = player.aabb
    for plat in platforms:
        if plat.tile_type == TileType.SPIKE:
            continue
        pa = plat.aabb
        if player_aabb.overlaps(pa):
            if player.vel.x > 0:
                player.pos.x = pa.x - PLAYER_W
            elif player.vel.x < 0:
                player.pos.x = pa.x + pa.w
            player.vel.x = 0

    # 垂直移动 + 碰撞
    player.pos.y += player.vel.y * dt
    player.on_ground = False
    player_aabb = player.aabb
    for plat in platforms:
        pa = plat.aabb
        if player_aabb.overlaps(pa):
            if plat.tile_type == TileType.SPIKE:
                if player.invincible_timer <= 0:
                    hurt_player(player)
                continue
            if player.vel.y > 0:
                player.pos.y = pa.y - PLAYER_H
                player.vel.y = 0
                player.on_ground = True
            elif player.vel.y < 0:
                player.pos.y = pa.y + pa.h
                player.vel.y = 0

    # 金币收集
    player_aabb = player.aabb
    for coin in coins:
        if not coin.collected:
            if player_aabb.overlaps(coin.aabb):
                coin.collected = True
                player.score += 10

    # 旗帜检测 (终点)
    flag_aabb = AABB(flag_pos.x, flag_pos.y, 16, 48)
    if player_aabb.overlaps(flag_aabb):
        player.win = True

    # 掉出地图
    if player.pos.y > WORLD_GROUND_Y + 200:
        hurt_player(player)
        if not player.dead:
            player.pos = Vec2(100, WORLD_GROUND_Y - PLAYER_H)
            player.vel = Vec2(0, 0)


def hurt_player(player: Player) -> None:
    """玩家受伤"""
    if player.invincible_timer > 0:
        return
    player.lives -= 1
    player.invincible_timer = 1.5
    if player.lives <= 0:
        player.dead = True


# ============================================================
#  渲染器 (合成画面)
# ============================================================

class GameCanvas:
    """
    游戏画面合成器

    将所有游戏元素渲染到一张 RGBA 图像上，
    然后交给 gpu-ascii 转换为 ASCII 输出。
    """

    def __init__(self, width: int, height: int, max_rows: int = 24, max_cols: int = 80):
        from PIL import Image
        self.width = width
        self.height = height
        self.max_rows = max_rows
        self.max_cols = max_cols
        self.img = Image.new("RGBA", (width, height), (135, 206, 235, 255))

        # 加载素材
        self._load_assets()

    def _load_assets(self):
        from PIL import Image

        def load(path, size=None):
            img = Image.open(path).convert("RGBA")
            if size:
                img = img.resize(size, Image.NEAREST)
            return img

        self.assets = {}
        self.assets["grass"] = load(TILES / "grass.png", (40, PLATFORM_H))
        self.assets["stone"] = load(TILES / "stone.png", (40, PLATFORM_H))
        self.assets["spike"] = load(TILES / "spike.png", (40, PLATFORM_H))
        self.assets["coin"] = load(TILES / "coin.png", (COIN_SIZE, COIN_SIZE))
        self.assets["heart"] = load(TILES / "heart.png", (16, 16))
        self.assets["flag"] = load(TILES / "flag.png", (16, 48))

        # 背景
        self.assets["cloud"] = load(BACKGROUNDS / "cloud.png", (80, 40))
        self.assets["mountain"] = load(BACKGROUNDS / "mountain.png", (120, 80))

        # 玩家帧
        self.player_frames = []
        for i in range(17):
            p = PLAYER_FRAMES / f"frame_{i:02d}.png"
            if p.exists():
                self.player_frames.append(load(p, (PLAYER_W, PLAYER_H)))
        if not self.player_frames:
            # 回退: 纯色方块
            fallback = self._make_fallback_player()
            self.player_frames = [fallback]

    def _make_fallback_player(self):
        from PIL import Image, ImageDraw
        img = Image.new("RGBA", (PLAYER_W, PLAYER_H), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        # 简易小人
        draw.rectangle([4, 0, 19, 8], fill=(255, 200, 150))    # 头
        draw.rectangle([6, 2, 10, 5], fill=(50, 50, 50))       # 左眼
        draw.rectangle([13, 2, 17, 5], fill=(50, 50, 50))      # 右眼
        draw.rectangle([2, 9, 21, 20], fill=(50, 100, 255))    # 身体
        draw.rectangle([2, 21, 10, 23], fill=(80, 60, 40))     # 左腿
        draw.rectangle([13, 21, 21, 23], fill=(80, 60, 40))    # 右腿
        return img

    def render_frame(self, player: Player, platforms: List[Platform],
                     coins: List[Coin], flag_pos: Vec2,
                     frame_index: int, elapsed: float,
                     debug: bool = False) -> Tuple[str, float, float]:
        """
        合成完整游戏画面并转为 ASCII

        Returns:
            ASCII 文本字符串
        """
        from PIL import Image

        # 相机跟随玩家 (水平居中，垂直偏下)
        cam_x = player.pos.x - self.width // 2 + PLAYER_W // 2
        # 垂直: 让玩家在屏幕下半部分 (60%位置)
        cam_y = player.pos.y - int(self.height * 0.6) + PLAYER_H // 2
        cam_x = max(0, cam_x)
        # 限制相机不要低于地面太多
        cam_y = max(0, min(cam_y, WORLD_GROUND_Y - self.height + 60))

        # 清空画布 (天空)
        self.img = Image.new("RGBA", (self.width, self.height), (135, 206, 235, 255))

        # 背景 - 远景山 (视差滚动)
        mountain_x = int(cam_x * 0.3) % 240
        for mx in range(-mountain_x, self.width + 120, 240):
            self.img.paste(self.assets["mountain"], (mx, self.height - 120),
                          self.assets["mountain"])

        # 背景 - 云 (慢速视差)
        cloud_offset = int(cam_x * 0.1)
        for ci in range(5):
            cx = (ci * 200 - cloud_offset) % (self.width + 200) - 100
            cy = 20 + ci * 15
            self.img.paste(self.assets["cloud"], (cx, cy), self.assets["cloud"])

        # 平台
        for plat in platforms:
            sx = int(plat.x - cam_x)
            sy = int(plat.y - cam_y)
            # 只渲染屏幕内的
            if sx + plat.width < -40 or sx > self.width + 40:
                continue
            if sy + PLATFORM_H < -40 or sy > self.height + 40:
                continue

            tile = self.assets.get(plat.tile_type.value, self.assets["grass"])
            # 平铺
            for tx in range(0, int(plat.width), 40):
                if 0 <= sx + tx < self.width:
                    self.img.paste(tile, (sx + tx, sy), tile)

        # 金币 (浮动动画)
        for coin in coins:
            if coin.collected:
                continue
            sx = int(coin.x - cam_x)
            bob = int(math.sin(elapsed * 3 + coin.x * 0.1) * 4)
            sy = int(coin.y - cam_y) + bob
            if 0 <= sx < self.width and 0 <= sy < self.height:
                self.img.paste(self.assets["coin"], (sx, sy), self.assets["coin"])

        # 旗帜
        fx = int(flag_pos.x - cam_x)
        fy = int(flag_pos.y - cam_y)
        if 0 <= fx < self.width:
            self.img.paste(self.assets["flag"], (fx, fy), self.assets["flag"])

        # 玩家
        px = int(player.pos.x - cam_x)
        py = int(player.pos.y - cam_y)

        # 选择动画帧
        if not player.on_ground:
            pframe = self.player_frames[min(2, len(self.player_frames) - 1)]
        elif abs(player.vel.x) > 10:
            walk_idx = (frame_index // 3) % len(self.player_frames)
            pframe = self.player_frames[walk_idx]
        else:
            pframe = self.player_frames[0]

        # 翻转
        if not player.facing_right:
            pframe = pframe.transpose(Image.FLIP_LEFT_RIGHT)

        # 无敌闪烁
        if player.invincible_timer <= 0 or int(elapsed * 10) % 2 == 0:
            # 先画一个亮色阴影/标记让角色位置醒目
            from PIL import ImageDraw
            draw = ImageDraw.Draw(self.img)
            shadow_y = py + PLAYER_H
            if 0 <= shadow_y < self.height:
                draw.rectangle([px + 4, shadow_y, px + PLAYER_W - 4, shadow_y + 2],
                               fill=(255, 255, 0))
            self.img.paste(pframe, (px, py), pframe)

        # HUD (直接画在画面上)
        self._draw_hud(player, elapsed)

        # 调试叠加层
        if debug:
            self.draw_debug_overlay(player, cam_x, cam_y)

        # 转为 ASCII
        text = self._to_ascii()
        return text, cam_x, cam_y

    def _draw_hud(self, player: Player, elapsed: float):
        from PIL import ImageDraw, ImageFont
        draw = ImageDraw.Draw(self.img)

        # 生命值
        for i in range(player.lives):
            hx = 8 + i * 20
            self.img.paste(self.assets["heart"], (hx, 8), self.assets["heart"])

        # 分数
        draw.text((self.width - 120, 8), f"SCORE: {player.score}", fill=(255, 255, 255))

        # 死亡/胜利提示
        if player.dead:
            draw.text((self.width // 2 - 60, self.height // 2 - 20),
                      "GAME OVER", fill=(255, 50, 50))
            draw.text((self.width // 2 - 80, self.height // 2 + 10),
                      "Press R to restart", fill=(255, 255, 255))
        elif player.win:
            draw.text((self.width // 2 - 50, self.height // 2 - 20),
                      "YOU WIN!", fill=(50, 255, 50))
            draw.text((self.width // 2 - 80, self.height // 2 + 10),
                      f"Score: {player.score}", fill=(255, 255, 255))

    def save_screenshot(self, path: str) -> str:
        """
        保存当前游戏画面截图 (原始像素, 非ASCII)

        Args:
            path: 保存路径

        Returns:
            保存的文件路径
        """
        self.img.save(path, format="PNG")
        return path

    def draw_debug_overlay(self, player: Player, cam_x: float, cam_y: float):
        """
        绘制调试叠加层: 碰撞箱、坐标信息

        Args:
            player: 玩家对象
            cam_x: 相机X偏移
            cam_y: 相机Y偏移
        """
        from PIL import ImageDraw
        draw = ImageDraw.Draw(self.img)

        # 玩家碰撞箱 (红色边框)
        px = int(player.pos.x - cam_x)
        py = int(player.pos.y - cam_y)
        draw.rectangle([px, py, px + PLAYER_W, py + PLAYER_H],
                       outline=(255, 0, 0), width=2)

        # 调试文字
        info = [
            f"POS: ({player.pos.x:.0f}, {player.pos.y:.0f})",
            f"VEL: ({player.vel.x:.0f}, {player.vel.y:.0f})",
            f"GROUND: {player.on_ground}",
            f"LIVES: {player.lives}",
            f"CAM: ({cam_x:.0f}, {cam_y:.0f})",
        ]
        y_offset = 30
        for line in info:
            draw.text((8, y_offset), line, fill=(255, 255, 0))
            y_offset += 14

    def _to_ascii(self) -> str:
        """将当前画面转为 ASCII 文本"""
        tmp = str(ASSETS / "_frame_tmp.png")
        # 确保文件完全写入磁盘
        self.img.save(tmp, format="PNG")
        with open(tmp, "rb") as f:
            f.read()

        # 复用 GPU 实例，避免每帧初始化
        if not hasattr(self, '_gpu') or self._gpu is None:
            self._gpu = GpuAscii()
        result = self._gpu.convert(tmp, cell_size=CELL_SIZE)

        # 截断到指定行列数
        lines = result.text.split('\n')
        if len(lines) > self.max_rows:
            lines = lines[:self.max_rows]
        lines = [line[:self.max_cols] for line in lines]

        return '\n'.join(lines)


# ============================================================
#  游戏主场景
# ============================================================

class PlatformerScene(Scene):
    """平台跳跃游戏场景"""

    def __init__(self):
        super().__init__("platformer")

        tw, th = measure_terminal_size()
        # 出血范围：底部留3行用于状态提示
        self.bleed_lines = 3
        self.terminal_height = th - self.bleed_lines
        self.terminal_width = tw
        
        # 画布尺寸: 每个ASCII字符对应 CELL_SIZE x (CELL_SIZE*2) 像素
        # 宽度 = 列数 * CELL_SIZE, 高度 = 行数 * CELL_SIZE * 2
        self.canvas_w = self.terminal_width * CELL_SIZE
        self.canvas_h = self.terminal_height * CELL_SIZE * 2

        self.canvas = GameCanvas(self.canvas_w, self.canvas_h,
                                 max_rows=self.terminal_height,
                                 max_cols=self.terminal_width)
        self.player = Player()
        self.platforms: List[Platform] = []
        self.coins: List[Coin] = []
        self.flag_pos = Vec2()

        self.frame_count = 0
        self.start_time = time.time()
        self.debug_mode = False
        self.screenshot_dir = ASSETS / "screenshots"
        self.screenshot_dir.mkdir(exist_ok=True)

        self._generate_level()

    def _generate_level(self):
        self.platforms, self.coins, self.flag_pos = generate_level(150)

    def restart(self):
        self.player = Player()
        self._generate_level()

    def update(self, dt: float, kb=None):
        if kb is None:
            return

        # 限制 dt 防止大跳帧导致穿模
        dt = min(dt, 0.05)

        # 重启
        if kb.just_pressed('r'):
            self.restart()
            return

        # 切换调试模式
        if kb.just_pressed('f'):
            self.debug_mode = not self.debug_mode
            print(f"Debug mode: {'ON' if self.debug_mode else 'OFF'}", file=sys.stderr)

        # 截屏 (保存原始画面)
        if kb.just_pressed('p'):
            ts = int(time.time() * 1000)
            path = str(self.screenshot_dir / f"shot_{ts}.png")
            self.canvas.save_screenshot(path)
            print(f"Screenshot saved: {path}", file=sys.stderr)

        update_player(self.player, self.platforms, self.coins,
                      self.flag_pos, dt, kb)
        self.frame_count += 1

    def render(self, renderer=None):
        elapsed = time.time() - self.start_time
        text, cam_x, cam_y = self.canvas.render_frame(
            self.player, self.platforms, self.coins,
            self.flag_pos, self.frame_count, elapsed,
            debug=self.debug_mode
        )
        # 直接输出到终端（已在_to_ascii中截断）
        print("\033[H\033[J" + text, end="", flush=True)


# ============================================================
#  主函数
# ============================================================

def main():
    print("=" * 50)
    print("  GPU-ASCII Platform Jumper")
    print("=" * 50)
    print()
    print("Controls:")
    print("  A/D or Left/Right - Move")
    print("  W or Space        - Jump")
    print("  R                 - Restart")
    print("  F                 - Toggle debug overlay")
    print("  P                 - Save screenshot")
    print("  Q                 - Quit")
    print()
    
    # 非交互模式下跳过等待
    if sys.stdin.isatty():
        try:
            input("Press Enter to start...")
        except EOFError:
            pass
    else:
        print("Starting automatically...")
        time.sleep(0.5)

    game_loop = GameLoop(target_fps=15)
    kb = RawKeyboard()
    scene = PlatformerScene()

    try:
        while game_loop.begin_frame():
            kb.poll()

            if kb.is_down('q'):
                break

            scene.update(game_loop.delta_time, kb)
            scene.render()

            game_loop.end_frame()

    except KeyboardInterrupt:
        print("\nGame interrupted.")
    finally:
        print("\nThanks for playing!")


if __name__ == "__main__":
    main()
