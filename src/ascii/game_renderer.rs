use anyhow::Result;
use crossterm::{
    cursor,
    style::{self},
    terminal::{self, ClearType, EnterAlternateScreen, LeaveAlternateScreen},
    ExecutableCommand,
};
use std::io::{self, Write};

/// 游戏模式渲染器 - 支持单页面动态刷新
pub struct GameRenderer {
    output: io::Stdout,
    initialized: bool,
    frame_count: u64,
    prev_grid: Option<Vec<Vec<char>>>,
    use_alternate: bool,
}

impl GameRenderer {
    /// 创建新的游戏渲染器
    pub fn new(_use_color: bool) -> Self {
        Self {
            output: io::stdout(),
            initialized: false,
            frame_count: 0,
            prev_grid: None,
            use_alternate: true,
        }
    }

    /// 初始化游戏模式终端（使用备用屏幕）
    pub fn init(&mut self) -> Result<()> {
        self.use_alternate = true;
        self.output.execute(EnterAlternateScreen)?;
        self.output.execute(terminal::Clear(ClearType::All))?;
        self.output.execute(cursor::Hide)?;
        self.output.flush()?;
        self.initialized = true;
        self.frame_count = 0;
        self.prev_grid = None;
        Ok(())
    }

    /// 初始化调试模式（不使用备用屏幕）
    pub fn init_debug(&mut self) -> Result<()> {
        self.use_alternate = false;
        self.output.execute(terminal::Clear(ClearType::All))?;
        self.output.execute(cursor::Hide)?;
        self.output.flush()?;
        self.initialized = true;
        self.frame_count = 0;
        self.prev_grid = None;
        Ok(())
    }

    /// 渲染一帧（完整重绘）
    pub fn render_frame(&mut self, grid: &[Vec<char>]) -> Result<()> {
        if !self.initialized {
            self.init()?;
        }

        // 移动到左上角
        self.output.execute(cursor::MoveTo(0, 0))?;

        let rows = grid.len();
        let cols = grid.first().map_or(0, |r| r.len());

        // 渲染每一行
        for (y, row) in grid.iter().enumerate() {
            self.output.execute(cursor::MoveTo(0, y as u16))?;
            for &ch in row {
                write!(self.output, "{}", ch)?;
            }
            // 用空格填充行尾
            for _ in row.len()..cols {
                write!(self.output, " ")?;
            }
        }

        // 清除可能的旧行（如果新帧比旧帧少行）
        if let Some(ref prev) = self.prev_grid {
            if rows < prev.len() {
                for y in rows..prev.len() {
                    self.output.execute(cursor::MoveTo(0, y as u16))?;
                    for _ in 0..cols {
                        write!(self.output, " ")?;
                    }
                }
            }
        }

        self.output.flush()?;
        self.frame_count += 1;
        self.prev_grid = Some(grid.to_vec());
        Ok(())
    }

    /// 渲染脏区域（只更新变化的cell）
    pub fn render_dirty(&mut self, grid: &[Vec<char>], prev_grid: &[Vec<char>]) -> Result<()> {
        if !self.initialized {
            self.init()?;
            return self.render_frame(grid);
        }

        let new_rows = grid.len();
        let new_cols = grid.first().map_or(0, |r| r.len());
        let prev_rows = prev_grid.len();
        let prev_cols = prev_grid.first().map_or(0, |r| r.len());
        let max_rows = new_rows.max(prev_rows);
        let max_cols = new_cols.max(prev_cols);

        let mut has_changes = false;

        for y in 0..max_rows {
            for x in 0..max_cols {
                let new_ch = grid.get(y).and_then(|r| r.get(x)).copied();
                let prev_ch = prev_grid.get(y).and_then(|r| r.get(x)).copied();

                if new_ch != prev_ch {
                    if !has_changes {
                        has_changes = true;
                    }
                    self.output.execute(cursor::MoveTo(x as u16, y as u16))?;
                    match new_ch {
                        Some(ch) => write!(self.output, "{}", ch)?,
                        None => write!(self.output, " ")?,
                    }
                }
            }
        }

        if has_changes {
            self.output.flush()?;
        }
        self.frame_count += 1;
        self.prev_grid = Some(grid.to_vec());
        Ok(())
    }

    /// 清理并恢复终端状态
    pub fn cleanup(&mut self) -> Result<()> {
        if self.initialized {
            self.output.execute(cursor::Show)?;
            self.output.execute(style::ResetColor)?;
            if self.use_alternate {
                self.output.execute(LeaveAlternateScreen)?;
            }
            self.output.flush()?;
            self.initialized = false;
            self.prev_grid = None;
        }
        Ok(())
    }

    /// 获取已渲染帧数
    pub fn frame_count(&self) -> u64 {
        self.frame_count
    }
}

impl Drop for GameRenderer {
    fn drop(&mut self) {
        let _ = self.cleanup();
    }
}
