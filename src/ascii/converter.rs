use anyhow::Result;
use image::DynamicImage;

use crate::gpu::{GpuContext, AsciiShader, AsciiParams};

pub struct AsciiConverter {
    gpu: GpuContext,
    shader: AsciiShader,
}

impl AsciiConverter {
    pub async fn new() -> Result<Self> {
        let gpu = GpuContext::new().await?;
        let shader = AsciiShader::new(&gpu)?;
        
        Ok(Self { gpu, shader })
    }

    pub fn convert(&self, image: &DynamicImage, cell_size: u32, char_ramp: &str) -> Result<Vec<Vec<char>>> {
        let rgba_image = image.to_rgba8();
        let (width, height) = rgba_image.dimensions();
        
        let texture = self.gpu.create_texture(
            width,
            height,
            wgpu::TextureFormat::Rgba8UnormSrgb,
            wgpu::TextureUsages::TEXTURE_BINDING | wgpu::TextureUsages::COPY_DST,
        );

        self.gpu.queue.write_texture(
            wgpu::ImageCopyTexture {
                texture: &texture,
                mip_level: 0,
                origin: wgpu::Origin3d::ZERO,
                aspect: wgpu::TextureAspect::All,
            },
            &rgba_image,
            wgpu::ImageDataLayout {
                offset: 0,
                bytes_per_row: Some(4 * width),
                rows_per_image: Some(height),
            },
            wgpu::Extent3d {
                width,
                height,
                depth_or_array_layers: 1,
            },
        );

        let params = AsciiParams {
            width,
            height,
            cell_size,
            char_count: char_ramp.len() as u32,
        };

        let indices = self.shader.execute(&self.gpu, &texture, &params)?;
        
        // 水平方向：每个cell显示 cell_size 像素
        // 垂直方向：每个cell显示 cell_size * 2 像素（因为ASCII字符高度是宽度的2倍）
        let grid_width = (width / cell_size) as usize;
        let grid_height = (height / (cell_size * 2)) as usize;
        let chars: Vec<char> = char_ramp.chars().collect();
        
        let mut result = Vec::with_capacity(grid_height);
        for y in 0..grid_height {
            let mut row = Vec::with_capacity(grid_width);
            for x in 0..grid_width {
                let idx = indices[y * grid_width + x] as usize;
                let ch = chars.get(idx).copied().unwrap_or(' ');
                row.push(ch);
            }
            result.push(row);
        }

        Ok(result)
    }

    pub fn convert_to_string(&self, image: &DynamicImage, cell_size: u32, char_ramp: &str) -> Result<String> {
        let grid = self.convert(image, cell_size, char_ramp)?;
        let lines: Vec<String> = grid.iter().map(|row| row.iter().collect()).collect();
        Ok(lines.join("\n"))
    }
}
