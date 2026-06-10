use anyhow::Result;
use crossterm::{
    cursor,
    style::{self, Color, Stylize},
    terminal::{self, ClearType},
    ExecutableCommand,
};
use std::io::{self, Write};

pub struct AsciiRenderer {
    output: io::Stdout,
    use_color: bool,
}

impl AsciiRenderer {
    pub fn new(use_color: bool) -> Self {
        Self {
            output: io::stdout(),
            use_color,
        }
    }

    pub fn clear(&mut self) -> Result<()> {
        self.output.execute(terminal::Clear(ClearType::All))?;
        self.output.execute(cursor::MoveTo(0, 0))?;
        Ok(())
    }

    pub fn render(&mut self, grid: &[Vec<char>], colors: Option<&[Vec<(u8, u8, u8)>]>) -> Result<()> {
        for (y, row) in grid.iter().enumerate() {
            for (x, &ch) in row.iter().enumerate() {
                if self.use_color {
                    if let Some(color_grid) = colors {
                        if let Some(&(r, g, b)) = color_grid.get(y).and_then(|row| row.get(x)) {
                            self.output.execute(style::SetForegroundColor(Color::Rgb { r, g, b }))?;
                        }
                    }
                }
                write!(self.output, "{}", ch)?;
            }
            writeln!(self.output)?;
        }
        self.output.flush()?;
        Ok(())
    }

    pub fn render_with_original_color(
        &mut self,
        grid: &[Vec<char>],
        original_image: &image::DynamicImage,
        cell_size: u32,
    ) -> Result<()> {
        let rgba = original_image.to_rgba8();
        let (width, height) = rgba.dimensions();
        
        for (y, row) in grid.iter().enumerate() {
            for (x, &ch) in row.iter().enumerate() {
                if self.use_color {
                    let px = (x as u32 * cell_size + cell_size / 2).min(width - 1);
                    let py = (y as u32 * cell_size + cell_size / 2).min(height - 1);
                    let pixel = rgba.get_pixel(px, py);
                    let (r, g, b) = (pixel[0], pixel[1], pixel[2]);
                    self.output.execute(style::SetForegroundColor(Color::Rgb { r, g, b }))?;
                }
                write!(self.output, "{}", ch)?;
            }
            writeln!(self.output)?;
        }
        self.output.flush()?;
        Ok(())
    }

    pub fn reset_color(&mut self) -> Result<()> {
        self.output.execute(style::ResetColor)?;
        Ok(())
    }
}
