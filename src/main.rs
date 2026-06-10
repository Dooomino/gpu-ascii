use anyhow::Result;
use clap::Parser;
use image::GenericImageView;

use gpu_ascii::ascii::{AsciiConverter, AsciiRenderer};
use gpu_ascii::cli::Args;

fn main() -> Result<()> {
    let args = Args::parse();
    
    let image = image::open(&args.image)?;
    let (orig_width, orig_height) = image.dimensions();
    
    let target_width = args.width.unwrap_or(orig_width);
    let target_height = args.height.unwrap_or(orig_height);
    
    let resized = if target_width != orig_width || target_height != orig_height {
        image.resize_exact(target_width, target_height, image::imageops::FilterType::Lanczos3)
    } else {
        image
    };
    
    let converter = pollster::block_on(AsciiConverter::new())?;
    let char_ramp = args.get_char_ramp();
    
    let grid = converter.convert(&resized, args.cell_size, char_ramp)?;
    
    let mut renderer = AsciiRenderer::new(args.color);
    
    if let Some(output_path) = &args.output {
        let lines: Vec<String> = grid.iter().map(|row| row.iter().collect()).collect();
        let content = lines.join("\n");
        std::fs::write(output_path, content)?;
        println!("Output saved to: {}", output_path.display());
    } else {
        renderer.clear()?;
        if args.color {
            renderer.render_with_original_color(&grid, &resized, args.cell_size)?;
        } else {
            renderer.render(&grid, None)?;
        }
        renderer.reset_color()?;
    }
    
    Ok(())
}
