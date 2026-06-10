use anyhow::Result;
use bytemuck::{Pod, Zeroable};
use super::context::GpuContext;

#[repr(C)]
#[derive(Copy, Clone, Pod, Zeroable)]
pub struct AsciiParams {
    pub width: u32,
    pub height: u32,
    pub cell_size: u32,
    pub char_count: u32,
}

#[repr(C)]
#[derive(Copy, Clone, Pod, Zeroable)]
pub struct ColorOutput {
    pub char_idx: u32,
    pub r: u32,
    pub g: u32,
    pub b: u32,
}

pub struct AsciiShader {
    pipeline: wgpu::ComputePipeline,
    bind_group_layout: wgpu::BindGroupLayout,
}

impl AsciiShader {
    pub fn new(gpu: &GpuContext) -> Result<Self> {
        let shader_source = include_str!("../../shaders/ascii.wgsl");
        let shader_module = gpu.device.create_shader_module(wgpu::ShaderModuleDescriptor {
            label: Some("ASCII Compute Shader"),
            source: wgpu::ShaderSource::Wgsl(shader_source.into()),
        });

        let bind_group_layout =
            gpu.device.create_bind_group_layout(&wgpu::BindGroupLayoutDescriptor {
                label: Some("ASCII Bind Group Layout"),
                entries: &[
                    wgpu::BindGroupLayoutEntry {
                        binding: 0,
                        visibility: wgpu::ShaderStages::COMPUTE,
                        ty: wgpu::BindingType::Buffer {
                            ty: wgpu::BufferBindingType::Uniform,
                            has_dynamic_offset: false,
                            min_binding_size: None,
                        },
                        count: None,
                    },
                    wgpu::BindGroupLayoutEntry {
                        binding: 1,
                        visibility: wgpu::ShaderStages::COMPUTE,
                        ty: wgpu::BindingType::Texture {
                            sample_type: wgpu::TextureSampleType::Float { filterable: false },
                            view_dimension: wgpu::TextureViewDimension::D2,
                            multisampled: false,
                        },
                        count: None,
                    },
                    wgpu::BindGroupLayoutEntry {
                        binding: 2,
                        visibility: wgpu::ShaderStages::COMPUTE,
                        ty: wgpu::BindingType::Buffer {
                            ty: wgpu::BufferBindingType::Storage { read_only: false },
                            has_dynamic_offset: false,
                            min_binding_size: None,
                        },
                        count: None,
                    },
                ],
            });

        let pipeline_layout =
            gpu.device.create_pipeline_layout(&wgpu::PipelineLayoutDescriptor {
                label: Some("ASCII Pipeline Layout"),
                bind_group_layouts: &[&bind_group_layout],
                push_constant_ranges: &[],
            });

        let pipeline = gpu.device.create_compute_pipeline(&wgpu::ComputePipelineDescriptor {
            label: Some("ASCII Compute Pipeline"),
            layout: Some(&pipeline_layout),
            module: &shader_module,
            entry_point: Some("main"),
            compilation_options: Default::default(),
            cache: None,
        });

        Ok(Self {
            pipeline,
            bind_group_layout,
        })
    }

    pub fn execute(
        &self,
        gpu: &GpuContext,
        texture: &wgpu::Texture,
        params: &AsciiParams,
    ) -> Result<Vec<u32>> {
        let grid_width = params.width / params.cell_size;
        let grid_height = params.height / params.cell_size;
        let output_size = (grid_width * grid_height) as usize;

        let params_buffer = gpu.create_buffer_init(
            "Params Buffer",
            bytemuck::cast_slice(&[*params]),
            wgpu::BufferUsages::UNIFORM,
        );

        let output_buffer = gpu.device.create_buffer(&wgpu::BufferDescriptor {
            label: Some("Output Buffer"),
            size: (output_size * std::mem::size_of::<u32>()) as u64,
            usage: wgpu::BufferUsages::STORAGE | wgpu::BufferUsages::COPY_SRC,
            mapped_at_creation: false,
        });

        let staging_buffer = gpu.device.create_buffer(&wgpu::BufferDescriptor {
            label: Some("Staging Buffer"),
            size: (output_size * std::mem::size_of::<u32>()) as u64,
            usage: wgpu::BufferUsages::MAP_READ | wgpu::BufferUsages::COPY_DST,
            mapped_at_creation: false,
        });

        let texture_view = texture.create_view(&wgpu::TextureViewDescriptor::default());

        let bind_group = gpu.device.create_bind_group(&wgpu::BindGroupDescriptor {
            label: Some("ASCII Bind Group"),
            layout: &self.bind_group_layout,
            entries: &[
                wgpu::BindGroupEntry {
                    binding: 0,
                    resource: params_buffer.as_entire_binding(),
                },
                wgpu::BindGroupEntry {
                    binding: 1,
                    resource: wgpu::BindingResource::TextureView(&texture_view),
                },
                wgpu::BindGroupEntry {
                    binding: 2,
                    resource: output_buffer.as_entire_binding(),
                },
            ],
        });

        let mut encoder = gpu.device.create_command_encoder(&wgpu::CommandEncoderDescriptor {
            label: Some("ASCII Command Encoder"),
        });

        {
            let mut compute_pass = encoder.begin_compute_pass(&wgpu::ComputePassDescriptor {
                label: Some("ASCII Compute Pass"),
                timestamp_writes: None,
            });

            compute_pass.set_pipeline(&self.pipeline);
            compute_pass.set_bind_group(0, &bind_group, &[]);
            compute_pass.dispatch_workgroups(
                (grid_width + 7) / 8,
                (grid_height + 7) / 8,
                1,
            );
        }

        encoder.copy_buffer_to_buffer(
            &output_buffer,
            0,
            &staging_buffer,
            0,
            (output_size * std::mem::size_of::<u32>()) as u64,
        );

        gpu.queue.submit(Some(encoder.finish()));

        let buffer_slice = staging_buffer.slice(..);
        let (sender, receiver) = flume::bounded(1);
        buffer_slice.map_async(wgpu::MapMode::Read, move |result| {
            sender.send(result).unwrap();
        });

        // 使用循环poll直到完成
        loop {
            if let Ok(result) = receiver.try_recv() {
                result?;
                break;
            }
            gpu.device.poll(wgpu::MaintainBase::Poll);
        }

        let data = buffer_slice.get_mapped_range();
        let result: Vec<u32> = bytemuck::cast_slice(&data).to_vec();

        drop(data);
        staging_buffer.unmap();

        Ok(result)
    }
}

pub struct ColorShader {
    pipeline: wgpu::ComputePipeline,
    bind_group_layout: wgpu::BindGroupLayout,
}

impl ColorShader {
    pub fn new(gpu: &GpuContext) -> Result<Self> {
        let shader_source = include_str!("../../shaders/ascii_color.wgsl");
        let shader_module = gpu.device.create_shader_module(wgpu::ShaderModuleDescriptor {
            label: Some("ASCII Color Compute Shader"),
            source: wgpu::ShaderSource::Wgsl(shader_source.into()),
        });

        let bind_group_layout =
            gpu.device.create_bind_group_layout(&wgpu::BindGroupLayoutDescriptor {
                label: Some("ASCII Color Bind Group Layout"),
                entries: &[
                    wgpu::BindGroupLayoutEntry {
                        binding: 0,
                        visibility: wgpu::ShaderStages::COMPUTE,
                        ty: wgpu::BindingType::Buffer {
                            ty: wgpu::BufferBindingType::Uniform,
                            has_dynamic_offset: false,
                            min_binding_size: None,
                        },
                        count: None,
                    },
                    wgpu::BindGroupLayoutEntry {
                        binding: 1,
                        visibility: wgpu::ShaderStages::COMPUTE,
                        ty: wgpu::BindingType::Texture {
                            sample_type: wgpu::TextureSampleType::Float { filterable: false },
                            view_dimension: wgpu::TextureViewDimension::D2,
                            multisampled: false,
                        },
                        count: None,
                    },
                    wgpu::BindGroupLayoutEntry {
                        binding: 2,
                        visibility: wgpu::ShaderStages::COMPUTE,
                        ty: wgpu::BindingType::Buffer {
                            ty: wgpu::BufferBindingType::Storage { read_only: false },
                            has_dynamic_offset: false,
                            min_binding_size: None,
                        },
                        count: None,
                    },
                ],
            });

        let pipeline_layout =
            gpu.device.create_pipeline_layout(&wgpu::PipelineLayoutDescriptor {
                label: Some("ASCII Color Pipeline Layout"),
                bind_group_layouts: &[&bind_group_layout],
                push_constant_ranges: &[],
            });

        let pipeline = gpu.device.create_compute_pipeline(&wgpu::ComputePipelineDescriptor {
            label: Some("ASCII Color Compute Pipeline"),
            layout: Some(&pipeline_layout),
            module: &shader_module,
            entry_point: Some("main"),
            compilation_options: Default::default(),
            cache: None,
        });

        Ok(Self {
            pipeline,
            bind_group_layout,
        })
    }

    pub fn execute(
        &self,
        gpu: &GpuContext,
        texture: &wgpu::Texture,
        params: &AsciiParams,
    ) -> Result<Vec<ColorOutput>> {
        let grid_width = params.width / params.cell_size;
        let cell_height = params.cell_size * 2;
        let grid_height = params.height / cell_height;
        let output_size = (grid_width * grid_height) as usize;

        let params_buffer = gpu.create_buffer_init(
            "Color Params Buffer",
            bytemuck::cast_slice(&[*params]),
            wgpu::BufferUsages::UNIFORM,
        );

        let output_buffer = gpu.device.create_buffer(&wgpu::BufferDescriptor {
            label: Some("Color Output Buffer"),
            size: (output_size * std::mem::size_of::<ColorOutput>()) as u64,
            usage: wgpu::BufferUsages::STORAGE | wgpu::BufferUsages::COPY_SRC,
            mapped_at_creation: false,
        });

        let staging_buffer = gpu.device.create_buffer(&wgpu::BufferDescriptor {
            label: Some("Color Staging Buffer"),
            size: (output_size * std::mem::size_of::<ColorOutput>()) as u64,
            usage: wgpu::BufferUsages::MAP_READ | wgpu::BufferUsages::COPY_DST,
            mapped_at_creation: false,
        });

        let texture_view = texture.create_view(&wgpu::TextureViewDescriptor::default());

        let bind_group = gpu.device.create_bind_group(&wgpu::BindGroupDescriptor {
            label: Some("ASCII Color Bind Group"),
            layout: &self.bind_group_layout,
            entries: &[
                wgpu::BindGroupEntry {
                    binding: 0,
                    resource: params_buffer.as_entire_binding(),
                },
                wgpu::BindGroupEntry {
                    binding: 1,
                    resource: wgpu::BindingResource::TextureView(&texture_view),
                },
                wgpu::BindGroupEntry {
                    binding: 2,
                    resource: output_buffer.as_entire_binding(),
                },
            ],
        });

        let mut encoder = gpu.device.create_command_encoder(&wgpu::CommandEncoderDescriptor {
            label: Some("ASCII Color Command Encoder"),
        });

        {
            let mut compute_pass = encoder.begin_compute_pass(&wgpu::ComputePassDescriptor {
                label: Some("ASCII Color Compute Pass"),
                timestamp_writes: None,
            });

            compute_pass.set_pipeline(&self.pipeline);
            compute_pass.set_bind_group(0, &bind_group, &[]);
            compute_pass.dispatch_workgroups(
                (grid_width + 7) / 8,
                (grid_height + 7) / 8,
                1,
            );
        }

        encoder.copy_buffer_to_buffer(
            &output_buffer,
            0,
            &staging_buffer,
            0,
            (output_size * std::mem::size_of::<ColorOutput>()) as u64,
        );

        gpu.queue.submit(Some(encoder.finish()));

        let buffer_slice = staging_buffer.slice(..);
        let (sender, receiver) = flume::bounded(1);
        buffer_slice.map_async(wgpu::MapMode::Read, move |result| {
            sender.send(result).unwrap();
        });

        loop {
            if let Ok(result) = receiver.try_recv() {
                result?;
                break;
            }
            gpu.device.poll(wgpu::MaintainBase::Poll);
        }

        let data = buffer_slice.get_mapped_range();
        let result: Vec<ColorOutput> = bytemuck::cast_slice(&data).to_vec();

        drop(data);
        staging_buffer.unmap();

        Ok(result)
    }
}
