// The same front that reverses plate gravity passes each fitting once.
export const pressureGLSL = /* glsl */`
float loadBehindFront(float passage) {
  float arrival = smoothstep(-12.0, 8.0, passage);
  float recovery = 1.0 - smoothstep(24.0, 126.0, passage);
  return min(uWave.y, 1.0) * arrival * recovery;
}
float pressureAt(vec2 gridPosition) {
  return loadBehindFront(uWave.x - length(gridPosition - uLode.xz));
}
`;
