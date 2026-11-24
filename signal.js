// Pure teaching models. Synthetic samples are never EEG experiment results.
export function syntheticSignal(length) {
  return Array.from({ length }, (_, i) => {
    const t = i / (length - 1);
    return (t < 0.5 ? 0.13 : 0.68) * Math.sin(2 * Math.PI * 8 * t) + 0.1 * Math.sin(2 * Math.PI * 21 * t);
  });
}
export function quantize(value, bits, method = 'uniform') {
  const mu = 255;
  const bounded = Math.max(-1, Math.min(1, value));
  const encoded = method === 'mulaw' ? Math.sign(bounded) * Math.log1p(mu * Math.abs(bounded)) / Math.log1p(mu) : bounded;
  const levels = 2 ** bits - 1;
  const rounded = 2 * Math.round((encoded + 1) / 2 * levels) / levels - 1;
  return method === 'mulaw' ? Math.sign(rounded) * Math.expm1(Math.abs(rounded) * Math.log1p(mu)) / mu : rounded;
}
export function signalPath(values, width, height, margin) {
  const w = width - margin.left - margin.right;
  const h = height - margin.top - margin.bottom;
  return values.map((value, i) => `${i ? 'L' : 'M'}${(margin.left + i / (values.length - 1) * w).toFixed(2)},${(margin.top + (1 - value) / 2 * h).toFixed(2)}`).join(' ');
}
