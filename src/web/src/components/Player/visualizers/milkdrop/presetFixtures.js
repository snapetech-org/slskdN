import { interfaceText, interfaceTextProps } from "../../../../lib/interfaceLocale";
const createDensePrimitiveFixtureSource = () => {
  const lines = [
    'name=Fixture Dense Primitive Pack',
    'decay=0.84',
    'wave_r=0.4',
    'wave_g=0.8',
    'wave_b=0.95',
  ];
  for (let index = 0; index < 40; index += 1) {
    const padded = String(index).padStart(2, '0');
    lines.push(`shape${padded}_enabled=1`);
    lines.push(`shape${padded}_sides=${3 + (index % 6)}`);
    lines.push(`shape${padded}_rad=${(0.035 + (index % 5) * 0.006).toFixed(3)}`);
    lines.push(`shape${padded}_x=${(0.08 + (index % 10) * 0.09).toFixed(3)}`);
    lines.push(`shape${padded}_y=${(0.12 + Math.floor(index / 10) * 0.2).toFixed(3)}`);
    lines.push(`shape${padded}_a=0.18`);
    lines.push(`shape${padded}_per_frame1=ang=time*${(0.05 + index * 0.001).toFixed(3)};`);
  }
  for (let index = 0; index < 20; index += 1) {
    lines.push(`wavecode_${index}_enabled=1`);
    lines.push(`wavecode_${index}_samples=32`);
    lines.push(`wavecode_${index}_r=${(0.25 + (index % 4) * 0.14).toFixed(3)}`);
    lines.push(`wavecode_${index}_g=${(0.45 + (index % 5) * 0.08).toFixed(3)}`);
    lines.push(`wavecode_${index}_b=${(0.75 - (index % 3) * 0.12).toFixed(3)}`);
    lines.push(`wavecode_${index}_a=0.34`);
    lines.push(`wavecode_${index}_per_point1=x=i;`);
    lines.push(`wavecode_${index}_per_point2=y=${(0.05 + index * 0.045).toFixed(3)}+sample*0.08;`);
  }
  return lines.join('\n');
};

export const nativeMilkdropFixturePack = [
  {
    get description() { return interfaceText("Classic feedback, warp grid, vectors, textured shape, and spectrum dots."); },
    id: 'classic-primitives',
    supported: true,
    source: `
      name=Fixture Classic Primitives
      decay=0.82
      wave_r=0.25
      wave_g=0.7
      wave_b=0.95
      wave_scale=1.4
      meshx=3
      meshy=2
      per_frame_1=rot=0.015*sin(time);
      per_pixel_1=dx=0.02*sin((x+time)*6.283);
      per_pixel_2=dy=0.02*cos((y+time)*6.283);
      mv_x=4
      mv_y=3
      mv_l=0.2
      mv_a=0.45
      shape00_enabled=1
      shape00_textured=1
      shape00_sides=5
      shape00_rad=0.22
      shape00_x=0.5
      shape00_y=0.5
      shape00_r=0.9
      shape00_g=0.85
      shape00_b=0.15
      shape00_a=0.45
      sprite00_enabled=1
      sprite00_image=fixture-logo.png
      sprite00_x=0.22
      sprite00_y=0.78
      sprite00_w=0.08
      sprite00_h=0.08
      sprite00_a=0.35
      wavecode_0_enabled=1
      wavecode_0_samples=32
      wavecode_0_spectrum=1
      wavecode_0_dots=1
      wavecode_0_r=0.8
      wavecode_0_g=1
      wavecode_0_b=0.3
      wavecode_0_a=0.9
      wavecode_0_per_point1=x=i;
      wavecode_0_per_point2=y=0.1+sample*0.65;
    `,
  },
  {
    get description() { return interfaceText("First shader subset with supported warp and comp ret assignments."); },
    id: 'shader-subset',
    supported: true,
    source: `
      name=Fixture Shader Subset
      decay=0.78
      wave_r=0.6
      wave_g=0.25
      wave_b=0.9
      warp_shader=shader_body {
      warp_shader_1=  float3 tint = vec3(0.8, 0.95, aspect);
      warp_shader_2=  float3 noise = tex2D(sampler_noise, uv).rgb;
      warp_shader_3=  ret = tex2D(sampler_main, uv).rgb * tint * noise;
      warp_shader_4=}
      comp_shader=shader_body {
      comp_shader_1=  ret = saturate(vec3(x, y, 0.45 + 0.35 * sin(time)));
      comp_shader_2=}
      shape00_enabled=1
      shape00_sides=6
      shape00_rad=0.14
      shape00_a=0.22
    `,
  },
  {
    get description() { return interfaceText("Simple MilkDrop3-style double preset parse fixture."); },
    id: 'milk2-double',
    supported: true,
    source: `
      [preset00]
      name=Fixture Double Left
      zoom=1
      per_frame_1=q33=sin(time);
      [preset01]
      name=Fixture Double Right
      blend_alpha=0.65
      zoom=0.9
      per_frame_1=q34=cos(time);
    `,
  },
  {
    get description() { return interfaceText("MilkDrop3-style q-register coverage across equations, primitives, and shaders."); },
    id: 'milkdrop3-q-registers',
    supported: true,
    source: `
      [preset00]
      name=Fixture Q Register Coverage A
      q64=0.64
      per_frame_1=q1=bass_att+q64;
      per_frame_2=q32=sin(time)+q1;
      warp_shader=ret = tex2D(sampler_main, uv).rgb * vec3(q1, q32, q64);
      wavecode_0_enabled=1
      wavecode_0_samples=16
      wavecode_0_per_frame1=q48=q32+0.1;
      wavecode_0_per_point1=y=sample+q48;
      [preset01]
      name=Fixture Q Register Coverage B
      blend_alpha=0.35
      composite_mode=screen
      per_frame_1=q63=treb_att+q2;
      comp_shader=ret = vec3(q2, q63, q64);
      shape00_enabled=1
      shape00_sides=4
      shape00_per_frame1=q64=max(q64,0.75);
      sprite00_enabled=1
      sprite00_image=fixture-logo.png
      sprite00_per_frame1=q16=q63*0.5;
    `,
  },
  {
    get description() { return interfaceText("MilkDrop3-style dense primitive count probe with many shapes and waves."); },
    id: 'milkdrop3-dense-primitives',
    supported: true,
    source: createDensePrimitiveFixtureSource(),
  },
  {
    get description() { return interfaceText("Unsupported shader control flow should be rejected cleanly."); },
    id: 'unsupported-control-flow-shader',
    supported: false,
    expectedError: 'shader translation pending: comp_shader',
    source: `
      name=Fixture Unsupported Shader
      wave_r=1
      comp_shader=for (;;) { ret = vec3(1.0); }
    `,
  },
];

export const getNativeMilkdropFixture = (id) =>
  nativeMilkdropFixturePack.find((fixture) => fixture.id === id);
