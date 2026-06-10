"""
GPU ASCII - Python绑定
使用ctypes调用Rust C ABI库
"""

import ctypes
import os
import sys
from pathlib import Path
from dataclasses import dataclass
from typing import Optional


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
    
    def __del__(self):
        """释放资源"""
        if hasattr(self, '_handle') and self._handle:
            self._lib.gpu_ascii_free(self._handle)
            self._handle = None


# 便捷函数
def image_to_ascii(
    image_path: str,
    cell_size: int = 8,
    char_ramp: str = " .:-=+*#%@",
    use_color: bool = False,
) -> str:
    """
    快速转换图像为ASCII文本
    
    Args:
        image_path: 图像文件路径
        cell_size: 单元格大小
        char_ramp: 字符集
        use_color: 是否输出颜色
        
    Returns:
        ASCII文本字符串
    """
    gpu = GpuAscii()
    result = gpu.convert(image_path, cell_size, char_ramp, use_color)
    return result.text
