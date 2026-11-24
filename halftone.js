import { makeZip, supportsZipLab } from "./zip.js";

// Floyd–Steinberg error diffusion, left-to-right, with no serpentine scan.
export function binarize(source, width, height, threshold, diffuse = false) {
  if (source.length !== width * height)
    throw new Error("Pixel dimensions do not match");
  const work = Float64Array.from(source);
  const result = new Uint8Array(source.length);
  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      const i = y * width + x;
      const value = work[i] >= threshold ? 255 : 0;
      result[i] = value;
      if (!diffuse) continue;
      const error = work[i] - value;
      if (x + 1 < width) work[i + 1] += (error * 7) / 16;
      if (y + 1 < height) {
        if (x > 0) work[i + width - 1] += (error * 3) / 16;
        work[i + width] += (error * 5) / 16;
        if (x + 1 < width) work[i + width + 1] += error / 16;
      }
    }
  }
  return result;
}

export function packBinary(pixels) {
  const packed = new Uint8Array(Math.ceil(pixels.length / 8));
  for (let i = 0; i < pixels.length; i++) {
    if (pixels[i] !== 0 && pixels[i] !== 255)
      throw new Error("Expected binary pixels");
    packed[i >> 3] |= (pixels[i] === 255 ? 1 : 0) << (7 - (i % 8));
  }
  return packed;
}

function paint(canvas, pixels, size) {
  canvas.width = canvas.height = size;
  const context = canvas.getContext("2d");
  const image = context.createImageData(size, size);
  for (let i = 0; i < pixels.length; i++) {
    image.data[4 * i] =
      image.data[4 * i + 1] =
      image.data[4 * i + 2] =
        pixels[i];
    image.data[4 * i + 3] = 255;
  }
  context.putImageData(image, 0, 0);
}

export function setUpHalftone() {
  const size = 128;
  const source = Uint8Array.from({ length: size * size }, (_, i) => {
    const x = i % size,
      y = Math.floor(i / size);
    if ((x - 93) ** 2 + (y - 36) ** 2 < 17 ** 2) return 75;
    return Math.round((255 * x) / (size - 1));
  });
  const byId = (id) => document.getElementById(id);
  let generation = 0;
  paint(byId("halftone-original"), source, size);
  async function update() {
    const current = ++generation;
    const threshold = Number(byId("halftone-threshold").value);
    byId("halftone-value").textContent = threshold;
    const binary = binarize(source, size, size, threshold);
    const dithered = binarize(source, size, size, threshold, true);
    paint(byId("halftone-binary"), binary, size);
    paint(byId("halftone-dithered"), dithered, size);
    const packed = [source, packBinary(binary), packBinary(dithered)];
    byId("halftone-sizes").textContent =
      `Pixel payload: grayscale ${source.length.toLocaleString()} B (8 bits/pixel); thresholded ${packed[1].length.toLocaleString()} B; dithered ${packed[2].length.toLocaleString()} B (both 1 bit/pixel). Measuring ZIP…`;
    try {
      if (!supportsZipLab())
        throw new Error("Raw DEFLATE is unavailable in this browser");
      const sizes = await Promise.all(
        packed.map(async (pixels) => (await makeZip(pixels)).length),
      );
      if (current !== generation) return;
      byId("halftone-sizes").textContent =
        `Packed pixel payloads: ${source.length.toLocaleString()} B grayscale; ${packed[1].length.toLocaleString()} B thresholded; ${packed[2].length.toLocaleString()} B dithered. Actual ZIP archives: ${sizes[0].toLocaleString()} B, ${sizes[1].toLocaleString()} B and ${sizes[2].toLocaleString()} B respectively.`;
    } catch (error) {
      if (current === generation)
        byId("halftone-sizes").textContent =
          `Pixel payloads: ${source.length} B grayscale, ${packed[1].length} B thresholded, ${packed[2].length} B dithered. ZIP unavailable: ${error.message}.`;
    }
  }
  byId("halftone-threshold").addEventListener("input", update);
  update();
}
