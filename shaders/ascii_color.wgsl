// GPU ASCII Color Compute Shader
// 输出字符索引和颜色信息

struct Params {
    width: u32,
    height: u32,
    cellSize: u32,
    charCount: u32,
}

struct ColorOutput {
    charIdx: u32,
    r: u32,
    g: u32,
    b: u32,
}

@group(0) @binding(0) var<uniform> params: Params;
@group(0) @binding(1) var inputTex: texture_2d<f32>;
@group(0) @binding(2) var<storage, read_write> output: array<ColorOutput>;

fn srgbToLinear(s: f32) -> f32 {
    return select(pow((s + 0.055) / 1.055, 2.4), s / 12.92, s <= 0.04045);
}

fn luminance(r: f32, g: f32, b: f32) -> f32 {
    return 0.2126 * srgbToLinear(r) + 0.7152 * srgbToLinear(g) + 0.0722 * srgbToLinear(b);
}

@compute @workgroup_size(8, 8)
fn main(@builtin(global_invocation_id) gid: vec3<u32>) {
    let cellX = gid.x;
    let cellY = gid.y;
    let gridW = params.width / params.cellSize;
    let cellHeight = params.cellSize * 2u;
    let gridH = params.height / cellHeight;
    
    if (cellX >= gridW || cellY >= gridH) {
        return;
    }

    var lumSum: f32 = 0.0;
    var rSum: f32 = 0.0;
    var gSum: f32 = 0.0;
    var bSum: f32 = 0.0;
    
    let startX = cellX * params.cellSize;
    let startY = cellY * cellHeight;
    let pixelCount = f32(params.cellSize * cellHeight);
    
    for (var dy: u32 = 0u; dy < cellHeight; dy++) {
        for (var dx: u32 = 0u; dx < params.cellSize; dx++) {
            let px = textureLoad(inputTex, vec2<i32>(i32(startX + dx), i32(startY + dy)), 0);
            lumSum += luminance(px.r, px.g, px.b);
            rSum += px.r;
            gSum += px.g;
            bSum += px.b;
        }
    }
    
    let avgLum = lumSum / pixelCount;
    let charIdx = clamp(u32(avgLum * f32(params.charCount - 1u)), 0u, params.charCount - 1u);
    
    // 平均颜色（转换为0-255）
    let avgR = clamp(u32(rSum / pixelCount * 255.0), 0u, 255u);
    let avgG = clamp(u32(gSum / pixelCount * 255.0), 0u, 255u);
    let avgB = clamp(u32(bSum / pixelCount * 255.0), 0u, 255u);
    
    let idx = cellY * gridW + cellX;
    output[idx] = ColorOutput(charIdx, avgR, avgG, avgB);
}
