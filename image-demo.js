// Actual browser PNG/JPEG encodes of a synthetic, opaque image.
// This teaching demonstration is independent of the EEG experiment exports.
const SIZE = 256;

function drawSource(pattern) {
  const canvas = document.createElement("canvas");
  canvas.width = canvas.height = SIZE;
  const context = canvas.getContext("2d", { willReadFrequently: true });
  if (pattern === "noise") {
    const pixels = context.createImageData(SIZE, SIZE);
    let state = 321;
    for (let i = 0; i < pixels.data.length; i += 4) {
      for (let c = 0; c < 3; c++) {
        state = (Math.imul(state, 1664525) + 1013904223) >>> 0;
        pixels.data[i + c] = state >>> 24;
      }
      pixels.data[i + 3] = 255;
    }
    context.putImageData(pixels, 0, 0);
  } else {
    const gradient = context.createLinearGradient(0, 0, SIZE, SIZE);
    gradient.addColorStop(0, "#15304a");
    gradient.addColorStop(0.5, "#86dbce");
    gradient.addColorStop(1, "#ffac8f");
    context.fillStyle = gradient;
    context.fillRect(0, 0, SIZE, SIZE);
    context.fillStyle = "#ffffff";
    context.fillRect(22, 24, 95, 95);
    context.fillStyle = "#101923";
    context.beginPath();
    context.arc(182, 76, 46, 0, Math.PI * 2);
    context.fill();
    for (let x = 15; x < 241; x += 4) context.fillRect(x, 145, 1, 76);
    context.fillStyle = "#ffffff";
    context.font = "bold 22px sans-serif";
    context.fillText("BITS & PIXELS", 27, 249);
  }
  return canvas;
}

function encode(canvas, type, quality) {
  return new Promise((resolve, reject) =>
    canvas.toBlob(
      (blob) => {
        if (!blob || blob.type !== type)
          reject(new Error(`${type} encoding is unavailable.`));
        else resolve(blob);
      },
      type,
      quality,
    ),
  );
}

export function setUpImageCompression() {
  const byId = (id) => document.getElementById(id);
  let generation = 0;
  let urls = [];
  let timer;
  async function update() {
    const current = ++generation;
    const quality = Number(byId("image-quality").value);
    byId("image-quality-value").textContent = `${quality} / 100`;
    byId("image-measurements").textContent = "Encoding and measuring…";
    try {
      const source = drawSource(byId("image-pattern").value);
      const [png, jpeg] = await Promise.all([
        encode(source, "image/png"),
        encode(source, "image/jpeg", quality / 100),
      ]);
      const bitmap = await createImageBitmap(jpeg);
      const decoded = document.createElement("canvas");
      decoded.width = decoded.height = SIZE;
      const context = decoded.getContext("2d", { willReadFrequently: true });
      context.drawImage(bitmap, 0, 0);
      bitmap.close();
      const a = source.getContext("2d").getImageData(0, 0, SIZE, SIZE).data;
      const b = context.getImageData(0, 0, SIZE, SIZE).data;
      let squaredError = 0;
      for (let i = 0; i < a.length; i += 4) {
        for (let channel = 0; channel < 3; channel++)
          squaredError += (a[i + channel] - b[i + channel]) ** 2;
      }
      if (current !== generation) return;
      const previousUrls = urls;
      urls = [URL.createObjectURL(png), URL.createObjectURL(jpeg)];
      byId("image-original").src = urls[0];
      byId("image-decoded").src = urls[1];
      previousUrls.forEach((url) => URL.revokeObjectURL(url));
      const rmse = Math.sqrt(squaredError / (SIZE * SIZE * 3));
      byId("image-measurements").textContent =
        `Measured PNG: ${png.size.toLocaleString()} B. JPEG: ${jpeg.size.toLocaleString()} B (${((100 * jpeg.size) / png.size).toFixed(1)}% of PNG). Decoded RGB RMSE: ${rmse.toFixed(2)} / 255.`;
    } catch (error) {
      if (current === generation)
        byId("image-measurements").textContent =
          `This browser could not run the demonstration: ${error.message}`;
    }
  }
  function schedule() {
    generation++; // Invalidate any previous encode immediately.
    clearTimeout(timer);
    byId("image-quality-value").textContent =
      `${byId("image-quality").value} / 100`;
    timer = setTimeout(update, 100);
  }
  byId("image-quality").addEventListener("input", schedule);
  byId("image-pattern").addEventListener("change", schedule);
  update();
}
