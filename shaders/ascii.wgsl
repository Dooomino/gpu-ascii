// GPU ASCII Compute Shader
// 将图像转换为ASCII字符索引

struct Params {
    width: u32,
    height: u32,
    cellSize: u32,
    charCount: u32,
}

@group(0) @binding(0) var<uniform> params: Params;
@group(0) @binding(1) var inputTex: texture_2d<f32>;
@group(0) @binding(2) var<storage, read_write> charIndices: array<u32>;

// sRGB到线性空间转换
fn srgbToLinear(s: f32) -> f32 {
    return select(pow((s + 0.055) / 1.055, 2.4), s / 12.92, s <= 0.04045);
}

// BT.709感知亮度计算
fn luminance(r: f32, g: f32, b: f32) -> f32 {
    return 0.2126 * srgbToLinear(r) + 0.7152 * srgbToLinear(g) + 0.0722 * srgbToLinear(b);
}

@compute @workgroup_size(8, 8)
fn main(@builtin(global_invocation_id) gid: vec3<u32>) {
    let cellX = gid.x;
    let cellY = gid.y;
    let gridW = params.width / params.cellSize;
    let gridH = params.height / params.cellSize;
    
    if (cellX >= gridW || cellY >= gridH) {
        return;
    }

    // 对cell内所有像素求平均亮度
    var sum: f32 = 0.0;
    let startX = cellX * params.cellSize;
    let startY = cellY * params.cellSize;
    
    for (var dy: u32 = 0u; dy < params.cellSize; dy++) {
        for (var dx: u32 = 0u; dx < params.cellSize; dx++) {
            let px = textureLoad(inputTex, vec2<i32>(i32(startX + dx), i32(startY + dy)), 0);
            sum += luminance(px.r, px.g, px.b);
        }
    }
    
    let avgLum = sum / f32(params.cellSize * params.cellSize);
    
    // 量化到字符索引
    let charIdx = u32(avgLum * f32(params.charCount - 1u));
    charIndices[cellY * gridW + cellX] = clamp(charIdx, 0u, params.charCount - 1u);
}
