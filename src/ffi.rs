use std::ffi::{CStr, CString};
use std::os::raw::c_char;
use std::ptr;

use crate::ascii::converter::AsciiConverter;

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
