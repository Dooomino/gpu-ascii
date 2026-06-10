"""
GPU ASCII - Python绑定
使用ctypes调用Rust C ABI库
"""

import ctypes
import os
import sys
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass
class AsciiResult:
    """ASCII转换结果"""
    text: str
    width: int
    height: int


class AsciiResultStruct(ctypes.Structure):
    """C结构体映射"""
    _fields_ = [
        ("data", ctypes.c_void_p),
        ("width", ctypes.c_uint32),
        ("height", ctypes.c_uint32),
        ("error", ctypes.c_void_p),
    ]


class ImageInfoStruct(ctypes.Structure):
    """图像信息结构体映射"""
    _fields_ = [
        ("width", ctypes.c_uint32),
        ("height", ctypes.c_uint32),
        ("error", ctypes.c_void_p),
    ]


def get_terminal_size() -> Tuple[int, int]:
    """
    获取终端大小
    
    Returns:
        (width, height) 终端列数和行数
    """
    try:
        size = os.get_terminal_size()
        return size.columns, size.lines
    except (AttributeError, ValueError, OSError):
        # 默认大小
        return 80, 24


class GpuAscii:
    """GPU加速的图像转ASCII工具"""
    
    def __init__(self, lib_path: Optional[str] = None):
        """
        初始化GPU ASCII
        
        Args:
            lib_path: 动态库路径，None则自动检测
        """
        if lib_path is None:
            lib_path = self._find_library()
        
        self._lib = ctypes.CDLL(lib_path)
        self._setup_functions()
        self._handle = self._lib.gpu_ascii_new()
        
        if not self._handle:
            raise RuntimeError("Failed to initialize GPU context")
    
    def _find_library(self) -> str:
        """自动查找动态库"""
        # 按平台确定库名
        if sys.platform == "win32":
            lib_name = "gpu_ascii.dll"
        elif sys.platform == "darwin":
            lib_name = "libgpu_ascii.dylib"
        else:
            lib_name = "libgpu_ascii.so"
        
        # 搜索路径
        search_paths = [
            Path(__file__).parent.parent / "target" / "release",
            Path(__file__).parent.parent / "target" / "debug",
            Path.cwd() / "target" / "release",
            Path.cwd() / "target" / "debug",
        ]
        
        for path in search_paths:
            lib_path = path / lib_name
            if lib_path.exists():
                return str(lib_path)
        
        raise FileNotFoundError(
            f"Cannot find {lib_name}. "
            f"Please build with: cargo build --release"
        )
    
    def _setup_functions(self):
        """设置函数签名"""
        # gpu_ascii_new
        self._lib.gpu_ascii_new.restype = ctypes.c_void_p
        self._lib.gpu_ascii_new.argtypes = []
        
        # gpu_ascii_free
        self._lib.gpu_ascii_free.restype = None
        self._lib.gpu_ascii_free.argtypes = [ctypes.c_void_p]
        
        # gpu_ascii_get_image_info
        self._lib.gpu_ascii_get_image_info.restype = ImageInfoStruct
        self._lib.gpu_ascii_get_image_info.argtypes = [
            ctypes.c_char_p,  # image_path
        ]
        
        # gpu_ascii_calc_cell_size
        self._lib.gpu_ascii_calc_cell_size.restype = ctypes.c_uint32
        self._lib.gpu_ascii_calc_cell_size.argtypes = [
            ctypes.c_uint32,  # img_width
            ctypes.c_uint32,  # img_height
            ctypes.c_uint32,  # terminal_width
            ctypes.c_uint32,  # terminal_height
        ]
        
        # gpu_ascii_convert
        self._lib.gpu_ascii_convert.restype = AsciiResultStruct
        self._lib.gpu_ascii_convert.argtypes = [
            ctypes.c_void_p,    # handle
            ctypes.c_char_p,    # image_path
            ctypes.c_uint32,    # cell_size
            ctypes.c_char_p,    # char_ramp
            ctypes.c_int,       # use_color (bool as int)
        ]
        
        # gpu_ascii_free_string
        self._lib.gpu_ascii_free_string.restype = None
        self._lib.gpu_ascii_free_string.argtypes = [ctypes.c_void_p]
        
        # ==================== 游戏模式函数 ====================
        
        # game_renderer_new
        self._lib.game_renderer_new.restype = ctypes.c_void_p
        self._lib.game_renderer_new.argtypes = []
        
        # game_renderer_free
        self._lib.game_renderer_free.restype = None
        self._lib.game_renderer_free.argtypes = [ctypes.c_void_p]
        
        # game_renderer_init
        self._lib.game_renderer_init.restype = ctypes.c_void_p
        self._lib.game_renderer_init.argtypes = [ctypes.c_void_p]
        
        # game_renderer_init_debug
        self._lib.game_renderer_init_debug.restype = ctypes.c_void_p
        self._lib.game_renderer_init_debug.argtypes = [ctypes.c_void_p]
        
        # game_renderer_cleanup
        self._lib.game_renderer_cleanup.restype = ctypes.c_void_p
        self._lib.game_renderer_cleanup.argtypes = [ctypes.c_void_p]
        
        # game_renderer_update
        self._lib.game_renderer_update.restype = FrameInfoStruct
        self._lib.game_renderer_update.argtypes = [
            ctypes.c_void_p,   # handle
            ctypes.c_char_p,   # image_path
            ctypes.c_uint32,   # cell_size
            ctypes.c_char_p,   # char_ramp
        ]
    
    def get_image_info(self, image_path: str) -> Tuple[int, int]:
        """
        获取图像尺寸信息
        
        Args:
            image_path: 图像文件路径
            
        Returns:
            (width, height) 图像宽度和高度
        """
        path_bytes = image_path.encode("utf-8")
        result = self._lib.gpu_ascii_get_image_info(path_bytes)
        
        if result.error:
            error_msg = ctypes.cast(result.error, ctypes.c_char_p).value.decode("utf-8")
            self._lib.gpu_ascii_free_string(result.error)
            raise RuntimeError(error_msg)
        
        return result.width, result.height
    
    def calc_cell_size(
        self,
        img_width: int,
        img_height: int,
        terminal_width: Optional[int] = None,
        terminal_height: Optional[int] = None,
    ) -> int:
        """
        计算适合终端的cell_size
        
        Args:
            img_width: 图像宽度
            img_height: 图像高度
            terminal_width: 终端宽度（列数），None则自动检测
            terminal_height: 终端高度（行数），None则自动检测
            
        Returns:
            推荐的cell_size
        """
        if terminal_width is None or terminal_height is None:
            tw, th = get_terminal_size()
            if terminal_width is None:
                terminal_width = tw
            if terminal_height is None:
                terminal_height = th
        
        return self._lib.gpu_ascii_calc_cell_size(
            img_width, img_height, terminal_width, terminal_height
        )
    
    def convert(
        self,
        image_path: str,
        cell_size: int = 8,
        char_ramp: str = " .:-=+*#%@",
        use_color: bool = False,
    ) -> AsciiResult:
        """
        转换图像为ASCII
        
        Args:
            image_path: 图像文件路径
            cell_size: 单元格大小(像素)
            char_ramp: 字符集
            use_color: 是否使用颜色
            
        Returns:
            AsciiResult包含文本和尺寸信息
        """
        path_bytes = image_path.encode("utf-8")
        ramp_bytes = char_ramp.encode("utf-8")
        
        result = self._lib.gpu_ascii_convert(
            self._handle,
            path_bytes,
            cell_size,
            ramp_bytes,
            1 if use_color else 0,
        )
        
        # 检查错误
        if result.error:
            error_msg = ctypes.cast(result.error, ctypes.c_char_p).value.decode("utf-8")
            self._lib.gpu_ascii_free_string(result.error)
            raise RuntimeError(error_msg)
        
        # 获取结果
        if result.data:
            text = ctypes.cast(result.data, ctypes.c_char_p).value.decode("utf-8")
            self._lib.gpu_ascii_free_string(result.data)
        else:
            text = ""
        
        return AsciiResult(
            text=text,
            width=result.width,
            height=result.height,
        )
    
    def convert_to_terminal(
        self,
        image_path: str,
        char_ramp: str = " .:-=+*#%@",
        use_color: bool = False,
        terminal_width: Optional[int] = None,
        terminal_height: Optional[int] = None,
        padding: int = 1,
    ) -> AsciiResult:
        """
        转换图像为ASCII，自动适应终端大小
        
        Args:
            image_path: 图像文件路径
            char_ramp: 字符集
            use_color: 是否使用颜色
            terminal_width: 终端宽度（列数），None则自动检测
            terminal_height: 终端高度（行数），None则自动检测
            padding: 边距（字符数）
            
        Returns:
            AsciiResult包含文本和尺寸信息
        """
        # 获取终端大小
        if terminal_width is None or terminal_height is None:
            tw, th = get_terminal_size()
            if terminal_width is None:
                terminal_width = tw
            if terminal_height is None:
                terminal_height = th
        
        # 减去边距
        terminal_width = max(10, terminal_width - padding * 2)
        terminal_height = max(5, terminal_height - padding * 2)
        
        # 获取图像尺寸
        img_width, img_height = self.get_image_info(image_path)
        
        # 计算合适的cell_size
        cell_size = self.calc_cell_size(
            img_width, img_height, terminal_width, terminal_height
        )
        
        # 转换图像
        return self.convert(image_path, cell_size, char_ramp, use_color)
    
    def __del__(self):
        """释放资源"""
        if hasattr(self, '_handle') and self._handle:
            self._lib.gpu_ascii_free(self._handle)
            self._handle = None


def image_to_ascii(
    image_path: str,
    cell_size: Optional[int] = None,
    char_ramp: str = " .:-=+*#%@",
    use_color: bool = False,
    fit_terminal: bool = False,
) -> str:
    """
    快速转换图像为ASCII文本
    
    Args:
        image_path: 图像文件路径
        cell_size: 单元格大小，None则自动计算
        char_ramp: 字符集
        use_color: 是否输出颜色
        fit_terminal: 是否自动适应终端大小
        
    Returns:
        ASCII文本字符串
    """
    gpu = GpuAscii()
    
    if fit_terminal:
        result = gpu.convert_to_terminal(image_path, char_ramp, use_color)
    elif cell_size is None:
        cell_size = 8
        result = gpu.convert(image_path, cell_size, char_ramp, use_color)
    else:
        result = gpu.convert(image_path, cell_size, char_ramp, use_color)
    
    return result.text


# ==================== 游戏模式 ====================

@dataclass
class FrameInfo:
    """帧更新信息"""
    dirty_cells: int
    total_cells: int
    grid_width: int
    grid_height: int


class FrameInfoStruct(ctypes.Structure):
    """帧信息结构体映射"""
    _fields_ = [
        ("dirty_cells", ctypes.c_uint32),
        ("total_cells", ctypes.c_uint32),
        ("grid_width", ctypes.c_uint32),
        ("grid_height", ctypes.c_uint32),
        ("error", ctypes.c_void_p),
    ]


class GameRenderer:
    """
    游戏模式渲染器 - 支持单页面动态刷新
    
    特性:
    - 光标定位+原地覆盖，无闪烁
    - 脏区域检测，只更新变化的cell
    - 支持上下文管理器和手动管理两种API
    
    使用示例:
        # 方式1: 上下文管理器
        with GameRenderer(gpu) as renderer:
            while running:
                renderer.update("frame.png")
        
        # 方式2: 手动管理
        renderer = GameRenderer(gpu)
        renderer.init()
        try:
            while running:
                renderer.update("frame.png")
        finally:
            renderer.cleanup()
    """
    
    def __init__(
        self,
        gpu: GpuAscii,
        char_ramp: str = " .:-=+*#%@",
    ):
        """
        创建游戏渲染器
        
        Args:
            gpu: GpuAscii实例
            char_ramp: 字符集
        """
        self._gpu = gpu
        self._char_ramp = char_ramp
        self._handle = gpu._lib.game_renderer_new()
        
        if not self._handle:
            raise RuntimeError("Failed to create game renderer")
    
    def __enter__(self):
        """上下文管理器入口"""
        self.init()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.cleanup()
        return False
    
    def init(self):
        """
        初始化游戏模式终端（使用备用屏幕）
        """
        error_ptr = self._gpu._lib.game_renderer_init(self._handle)
        if error_ptr:
            error_msg = ctypes.cast(error_ptr, ctypes.c_char_p).value.decode("utf-8")
            self._gpu._lib.gpu_ascii_free_string(error_ptr)
            raise RuntimeError(error_msg)
    
    def init_debug(self):
        """
        初始化调试模式（不使用备用屏幕，支持input()）
        """
        error_ptr = self._gpu._lib.game_renderer_init_debug(self._handle)
        if error_ptr:
            error_msg = ctypes.cast(error_ptr, ctypes.c_char_p).value.decode("utf-8")
            self._gpu._lib.gpu_ascii_free_string(error_ptr)
            raise RuntimeError(error_msg)
    
    def cleanup(self):
        """
        恢复终端状态
        - 显示光标
        - 移动光标到内容下方
        """
        error_ptr = self._gpu._lib.game_renderer_cleanup(self._handle)
        if error_ptr:
            error_msg = ctypes.cast(error_ptr, ctypes.c_char_p).value.decode("utf-8")
            self._gpu._lib.gpu_ascii_free_string(error_ptr)
            raise RuntimeError(error_msg)
    
    def update(
        self,
        image_path: str,
        cell_size: int = 8,
    ) -> FrameInfo:
        """
        更新一帧（渲染到终端）
        
        Args:
            image_path: 图像文件路径
            cell_size: 单元格大小
            
        Returns:
            FrameInfo包含脏区域统计信息
        """
        path_bytes = image_path.encode("utf-8")
        ramp_bytes = self._char_ramp.encode("utf-8")
        
        result = self._gpu._lib.game_renderer_update(
            self._handle,
            path_bytes,
            cell_size,
            ramp_bytes,
        )
        
        if result.error:
            error_msg = ctypes.cast(result.error, ctypes.c_char_p).value.decode("utf-8")
            self._gpu._lib.gpu_ascii_free_string(result.error)
            raise RuntimeError(error_msg)
        
        return FrameInfo(
            dirty_cells=result.dirty_cells,
            total_cells=result.total_cells,
            grid_width=result.grid_width,
            grid_height=result.grid_height,
        )
    
    def update_to_terminal(
        self,
        image_path: str,
        padding: int = 1,
    ) -> FrameInfo:
        """
        更新一帧，自动适配终端大小
        
        Args:
            image_path: 图像文件路径
            padding: 边距（字符数）
            
        Returns:
            FrameInfo包含脏区域统计信息
        """
        # 获取终端大小
        tw, th = get_terminal_size()
        terminal_width = max(10, tw - padding * 2)
        terminal_height = max(5, th - padding * 2)
        
        # 获取图像尺寸
        img_width, img_height = self._gpu.get_image_info(image_path)
        
        # 计算合适的cell_size
        cell_size = self._gpu.calc_cell_size(
            img_width, img_height, terminal_width, terminal_height
        )
        
        return self.update(image_path, cell_size)
    
    def __del__(self):
        """释放资源"""
        if hasattr(self, '_handle') and self._handle:
            self._gpu._lib.game_renderer_free(self._handle)
            self._handle = None
