pub mod converter;
pub mod renderer;

pub use converter::AsciiConverter;
pub use renderer::AsciiRenderer;

pub const DEFAULT_CHAR_RAMP: &str = " .:-=+*#%@";
pub const DENSE_CHAR_RAMP: &str = " .:;+=xX$#@█";
pub const MINIMAL_CHAR_RAMP: &str = " ·░█";
pub const BLOCK_CHAR_RAMP: &str = " ░▒▓█";
