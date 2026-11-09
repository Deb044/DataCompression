# Compression Lab

An interactive DA3021 course project about lossless and lossy compression. The overview and ZIP module are available. The MP3 tab is reserved for the next module.

## Run locally

From the repository folder, start a static server:

```sh
python -m http.server 8000
```

Open `http://localhost:8000`. Use a browser that supports raw DEFLATE through `CompressionStream` and `DecompressionStream`. There are no package installs, external scripts, or build steps.

## What's in the lab

- `index.html` and `styles.css` contain the lesson and layout.
- `app.js` connects the tabs, teaching controls, and experiment charts.
- `samples.js` generates reproducible byte samples and implements the small LZ77 and Huffman teaching models.
- `zip.js` builds one-entry ZIP archives around the browser's DEFLATE stream. Repeated ZIP results include the archive headers and stop at the first pass that does not shrink the file, or at eight passes. The lab verifies that unpacking all layers recovers the original bytes.

The illustrative token model is separate from the real compressor. The browser measures all displayed archive sizes when an experiment runs. The fixed initial seed lets you reproduce the input, and different browser compressors may produce slightly different archive sizes.
