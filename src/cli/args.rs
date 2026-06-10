use clap::Parser;
use std::path::PathBuf;

#[derive(Parser, Debug)]
#[command(name = "gpu-ascii")]
#[command(about = "GPU-accelerated image to ASCII art converter")]
#[command(version)]
pub struct Args {
    /// Input image file path
    #[arg(value_name = "IMAGE")]
    pub image: PathBuf,

    /// Cell size in pixels (default: 8)
    #[arg(short, long, default_value = "8")]
    pub cell_size: u32,

    /// Character ramp preset
    #[arg(short, long, value_enum, default_value = "default")]
    pub ramp: RampPreset,

    /// Custom character ramp string
    #[arg(long)]
    pub custom_ramp: Option<String>,

    /// Enable colored output
    #[arg(short, long)]
    pub color: bool,

    /// Output width in characters (auto if not specified)
    #[arg(short, long)]
    pub width: Option<u32>,

    /// Output height in characters (auto if not specified)
    #[arg(long)]
    pub height: Option<u32>,

    /// Output to file instead of stdout
    #[arg(short, long)]
    pub output: Option<PathBuf>,
}

#[derive(clap::ValueEnum, Clone, Debug)]
pub enum RampPreset {
    Default,
    Dense,
    Minimal,
    Block,
    Detailed,
}

impl RampPreset {
    pub fn char_ramp(&self) -> &str {
        match self {
            RampPreset::Default => " .:-=+*#%@",
            RampPreset::Dense => " .:;+=xX$#@█",
            RampPreset::Minimal => " ·░█",
            RampPreset::Block => " ░▒▓█",
            RampPreset::Detailed => " .'`^\",:;Il!i><~+_-?][}{1)(|\\/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$",
        }
    }
}

impl Args {
    pub fn get_char_ramp(&self) -> &str {
        self.custom_ramp.as_deref().unwrap_or_else(|| self.ramp.char_ramp())
    }
}
