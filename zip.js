// The lab writes ordinary ZIP archives with one entry and no extra fields.
// The browser supplies raw DEFLATE. This module supplies the ZIP container.
const LOCAL_HEADER = 30;
const CENTRAL_HEADER = 46;
const END_RECORD = 22;
const ENTRY_NAME = new TextEncoder().encode("payload.bin");
const CRC_TABLE = Uint32Array.from({ length: 256 }, (_, value) => {
  for (let bit = 0; bit < 8; bit++) {
    value = (value >>> 1) ^ (value & 1 ? 0xedb88320 : 0);
  }
  return value;
});

function crc32(bytes) {
  let crc = 0xffffffff;
  for (const byte of bytes) crc = (crc >>> 8) ^ CRC_TABLE[(crc ^ byte) & 0xff];
  return (crc ^ 0xffffffff) >>> 0;
}

async function readStream(bytes, transform) {
  const stream = new Blob([bytes]).stream().pipeThrough(transform);
  return new Uint8Array(await new Response(stream).arrayBuffer());
}

export function supportsZipLab() {
  try {
    new CompressionStream("deflate-raw");
    return true;
  } catch {
    return false;
  }
}

export async function makeZip(input) {
  const compressed = await readStream(
    input,
    new CompressionStream("deflate-raw"),
  );
  const checksum = crc32(input);
  const dataOffset = LOCAL_HEADER + ENTRY_NAME.length;
  const centralOffset = dataOffset + compressed.length;
  const centralSize = CENTRAL_HEADER + ENTRY_NAME.length;
  const endOffset = centralOffset + centralSize;
  const archive = new Uint8Array(endOffset + END_RECORD);
  const header = new DataView(archive.buffer);

  // Local file header. The fixed DOS date is 1 January 1980.
  header.setUint32(0, 0x04034b50, true);
  header.setUint16(4, 20, true);
  header.setUint16(8, 8, true);
  header.setUint16(12, 0x21, true);
  header.setUint32(14, checksum, true);
  header.setUint32(18, compressed.length, true);
  header.setUint32(22, input.length, true);
  header.setUint16(26, ENTRY_NAME.length, true);
  archive.set(ENTRY_NAME, LOCAL_HEADER);
  archive.set(compressed, dataOffset);

  // Central directory entry mirrors the local header and points back to it.
  header.setUint32(centralOffset, 0x02014b50, true);
  header.setUint16(centralOffset + 4, 20, true);
  header.setUint16(centralOffset + 6, 20, true);
  header.setUint16(centralOffset + 10, 8, true);
  header.setUint16(centralOffset + 14, 0x21, true);
  header.setUint32(centralOffset + 16, checksum, true);
  header.setUint32(centralOffset + 20, compressed.length, true);
  header.setUint32(centralOffset + 24, input.length, true);
  header.setUint16(centralOffset + 28, ENTRY_NAME.length, true);
  archive.set(ENTRY_NAME, centralOffset + CENTRAL_HEADER);

  // End of central directory. All unused fields are zero.
  header.setUint32(endOffset, 0x06054b50, true);
  header.setUint16(endOffset + 8, 1, true);
  header.setUint16(endOffset + 10, 1, true);
  header.setUint32(endOffset + 12, centralSize, true);
  header.setUint32(endOffset + 16, centralOffset, true);
  return archive;
}
