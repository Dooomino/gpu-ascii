use std::ffi::{CStr, CString};
use std::os::raw::c_char;
use std::ptr;

use image::GenericImageView;
use crate::ascii::converter::AsciiConverter;
use crate::ascii::game_renderer::GameRenderer;

pub struct GpuAsciiHandle {
    converter: AsciiConverter,
}

#[repr(C)]
pub struct AsciiResult {
    pub data: *mut c_char,
    pub width: u32,
    pub height: u32,
    pub error: *mut c_char,
}

#[repr(C)]
pub struct ImageInfo {
    pub width: u32,
    pub height: u32,
    pub error: *mut c_char,
}

#[no_mangle]
pub extern "C" fn gpu_ascii_new() -> *mut GpuAsciiHandle {
    let converter = match pollster::block_on(AsciiConverter::new()) {
        Ok(c) => c,
        Err(_) => return ptr::null_mut(),
    };

    Box::into_raw(Box::new(GpuAsciiHandle { converter }))
}

#[no_mangle]
pub extern "C" fn gpu_ascii_free(handle: *mut GpuAsciiHandle) {
    if !handle.is_null() {
        unsafe {
            drop(Box::from_raw(handle));
        }
    }
}

#[no_mangle]
pub extern "C" fn gpu_ascii_get_image_info(
    image_path: *const c_char,
) -> ImageInfo {
    if image_path.is_null() {
        return ImageInfo {
            width: 0,
            height: 0,
            error: CString::new("Invalid path").unwrap().into_raw(),
        };
    }

    let path_str = match unsafe { CStr::from_ptr(image_path) }.to_str() {
        Ok(s) => s,
        Err(e) => {
            return ImageInfo {
                width: 0,
                height: 0,
                error: CString::new(format!("Invalid path: {}", e)).unwrap().into_raw(),
            };
        }
    };

    match image::open(path_str) {
        Ok(img) => {
            let (w, h) = img.dimensions();
            ImageInfo {
                width: w,
                height: h,
                error: ptr::null_mut(),
            }
        }
        Err(e) => ImageInfo {
            width: 0,
            height: 0,
            error: CString::new(format!("Failed to load image: {}", e)).unwrap().into_raw(),
        },
    }
}

#[no_mangle]
pub extern "C" fn gpu_ascii_calc_cell_size(
    img_width: u32,
    img_height: u32,
    terminal_width: u32,
    terminal_height: u32,
) -> u32 {
    if img_width == 0 || img_height == 0 || terminal_width == 0 || terminal_height == 0 {
        return 8;
    }

    // ASCII字符高度约是宽度的2倍
    // 水平方向：每个cell显示 cell_size 像素
    // 垂直方向：每个cell显示 cell_size * 2 像素（因为字符高度是宽度的2倍）
    
    // 计算让图像完整显示所需的cell_size
    let cell_by_width = img_width as f64 / terminal_width as f64;
    let cell_by_height = img_height as f64 / (terminal_height as f64 * 2.0);

    // 取较大的cell_size以确保图像完全显示在终端内
    let cell_size = cell_by_width.max(cell_by_height);

    // 限制范围在2-32之间，并取整
    cell_size.max(2.0).min(32.0).ceil() as u32
}

#[no_mangle]
pub extern "C" fn gpu_ascii_convert(
    handle: *mut GpuAsciiHandle,
    image_path: *const c_char,
    cell_size: u32,
    char_ramp: *const c_char,
    _use_color: bool,
) -> AsciiResult {
    if handle.is_null() || image_path.is_null() {
        return AsciiResult {
            data: ptr::null_mut(),
            width: 0,
            height: 0,
            error: CString::new("Invalid handle or path").unwrap().into_raw(),
        };
    }

    let handle_ref = unsafe { &*handle };
    
    let path_str = match unsafe { CStr::from_ptr(image_path) }.to_str() {
        Ok(s) => s,
        Err(e) => {
            return AsciiResult {
                data: ptr::null_mut(),
                width: 0,
                height: 0,
                error: CString::new(format!("Invalid path: {}", e)).unwrap().into_raw(),
            };
        }
    };

    let ramp = if char_ramp.is_null() {
        " .:-=+*#%@"
    } else {
        match unsafe { CStr::from_ptr(char_ramp) }.to_str() {
            Ok(s) => s,
            Err(e) => {
                return AsciiResult {
                    data: ptr::null_mut(),
                    width: 0,
                    height: 0,
                    error: CString::new(format!("Invalid ramp: {}", e)).unwrap().into_raw(),
                };
            }
        }
    };

    let image = match image::open(path_str) {
        Ok(img) => img,
        Err(e) => {
            return AsciiResult {
                data: ptr::null_mut(),
                width: 0,
                height: 0,
                error: CString::new(format!("Failed to load image: {}", e)).unwrap().into_raw(),
            };
        }
    };

    let grid = match handle_ref.converter.convert(&image, cell_size, ramp) {
        Ok(g) => g,
        Err(e) => {
            return AsciiResult {
                data: ptr::null_mut(),
                width: 0,
                height: 0,
                error: CString::new(format!("Conversion failed: {}", e)).unwrap().into_raw(),
            };
        }
    };

    let height = grid.len() as u32;
    let width = grid.first().map_or(0, |row| row.len() as u32);
    
    let lines: Vec<String> = grid.iter().map(|row| row.iter().collect()).collect();
    let output = lines.join("\n");
    
    match CString::new(output) {
        Ok(c_str) => AsciiResult {
            data: c_str.into_raw(),
            width,
            height,
            error: ptr::null_mut(),
        },
        Err(e) => AsciiResult {
            data: ptr::null_mut(),
            width: 0,
            height: 0,
            error: CString::new(format!("Null byte in output: {}", e)).unwrap().into_raw(),
        },
    }
}

#[no_mangle]
pub extern "C" fn gpu_ascii_free_string(s: *mut c_char) {
    if !s.is_null() {
        unsafe {
            drop(CString::from_raw(s));
        }
    }
}

// ==================== 游戏模式 API ====================

pub struct GameRendererHandle {
    converter: AsciiConverter,
    renderer: GameRenderer,
    prev_frame: Option<Vec<Vec<char>>>,
}

#[repr(C)]
pub struct FrameInfo {
    pub dirty_cells: u32,
    pub total_cells: u32,
    pub grid_width: u32,
    pub grid_height: u32,
    pub error: *mut c_char,
}

#[no_mangle]
pub extern "C" fn game_renderer_new() -> *mut GameRendererHandle {
    let converter = match pollster::block_on(AsciiConverter::new()) {
        Ok(c) => c,
        Err(_) => return ptr::null_mut(),
    };

    let renderer = GameRenderer::new(false);

    Box::into_raw(Box::new(GameRendererHandle {
        converter,
        renderer,
        prev_frame: None,
    }))
}

#[no_mangle]
pub extern "C" fn game_renderer_free(handle: *mut GameRendererHandle) {
    if !handle.is_null() {
        unsafe {
            let _ = (*handle).renderer.cleanup();
            drop(Box::from_raw(handle));
        }
    }
}

#[no_mangle]
pub extern "C" fn game_renderer_init(handle: *mut GameRendererHandle) -> *mut c_char {
    if handle.is_null() {
        return CString::new("Invalid handle").unwrap().into_raw();
    }

    let handle_ref = unsafe { &mut *handle };
    match handle_ref.renderer.init() {
        Ok(_) => ptr::null_mut(),
        Err(e) => CString::new(format!("{}", e)).unwrap().into_raw(),
    }
}

#[no_mangle]
pub extern "C" fn game_renderer_init_debug(handle: *mut GameRendererHandle) -> *mut c_char {
    if handle.is_null() {
        return CString::new("Invalid handle").unwrap().into_raw();
    }

    let handle_ref = unsafe { &mut *handle };
    match handle_ref.renderer.init_debug() {
        Ok(_) => ptr::null_mut(),
        Err(e) => CString::new(format!("{}", e)).unwrap().into_raw(),
    }
}

#[no_mangle]
pub extern "C" fn game_renderer_cleanup(handle: *mut GameRendererHandle) -> *mut c_char {
    if handle.is_null() {
        return CString::new("Invalid handle").unwrap().into_raw();
    }

    let handle_ref = unsafe { &mut *handle };
    match handle_ref.renderer.cleanup() {
        Ok(_) => ptr::null_mut(),
        Err(e) => CString::new(format!("{}", e)).unwrap().into_raw(),
    }
}

#[no_mangle]
pub extern "C" fn game_renderer_update(
    handle: *mut GameRendererHandle,
    image_path: *const c_char,
    cell_size: u32,
    char_ramp: *const c_char,
) -> FrameInfo {
    if handle.is_null() || image_path.is_null() {
        return FrameInfo {
            dirty_cells: 0,
            total_cells: 0,
            grid_width: 0,
            grid_height: 0,
            error: CString::new("Invalid handle or path").unwrap().into_raw(),
        };
    }

    let handle_ref = unsafe { &mut *handle };

    let path_str = match unsafe { CStr::from_ptr(image_path) }.to_str() {
        Ok(s) => s,
        Err(e) => {
            return FrameInfo {
                dirty_cells: 0,
                total_cells: 0,
                grid_width: 0,
                grid_height: 0,
                error: CString::new(format!("Invalid path: {}", e)).unwrap().into_raw(),
            };
        }
    };

    let ramp = if char_ramp.is_null() {
        " .:-=+*#%@"
    } else {
        match unsafe { CStr::from_ptr(char_ramp) }.to_str() {
            Ok(s) => s,
            Err(e) => {
                return FrameInfo {
                    dirty_cells: 0,
                    total_cells: 0,
                    grid_width: 0,
                    grid_height: 0,
                    error: CString::new(format!("Invalid ramp: {}", e)).unwrap().into_raw(),
                };
            }
        }
    };

    let image = match image::open(path_str) {
        Ok(img) => img,
        Err(e) => {
            return FrameInfo {
                dirty_cells: 0,
                total_cells: 0,
                grid_width: 0,
                grid_height: 0,
                error: CString::new(format!("Failed to load image: {}", e)).unwrap().into_raw(),
            };
        }
    };

    let grid = match handle_ref.converter.convert(&image, cell_size, ramp) {
        Ok(g) => g,
        Err(e) => {
            return FrameInfo {
                dirty_cells: 0,
                total_cells: 0,
                grid_width: 0,
                grid_height: 0,
                error: CString::new(format!("Conversion failed: {}", e)).unwrap().into_raw(),
            };
        }
    };

    let grid_height = grid.len() as u32;
    let grid_width = grid.first().map_or(0, |row| row.len() as u32);
    let total_cells = grid_width * grid_height;

    // 计算脏区域
    let dirty_cells = if let Some(ref prev) = handle_ref.prev_frame {
        let mut count = 0;
        for (y, row) in grid.iter().enumerate() {
            for (x, &ch) in row.iter().enumerate() {
                if prev.get(y).and_then(|r| r.get(x)) != Some(&ch) {
                    count += 1;
                }
            }
        }
        count
    } else {
        total_cells
    };

    // 渲染帧
    let render_result = if handle_ref.prev_frame.is_some() {
        handle_ref.renderer.render_dirty(&grid, handle_ref.prev_frame.as_ref().unwrap())
    } else {
        handle_ref.renderer.render_frame(&grid)
    };

    if let Err(e) = render_result {
        return FrameInfo {
            dirty_cells: 0,
            total_cells,
            grid_width,
            grid_height,
            error: CString::new(format!("Render failed: {}", e)).unwrap().into_raw(),
        };
    }

    // 更新上一帧
    handle_ref.prev_frame = Some(grid);

    FrameInfo {
        dirty_cells,
        total_cells,
        grid_width,
        grid_height,
        error: ptr::null_mut(),
    }
}
