export const SAMPLE_SIZE = 256 * 1024;
export const DEFAULT_SEED = 321;

// A seeded generator makes the default experiment reproducible.
export function randomGenerator(seed) {
  let state = seed >>> 0;
  return () => {
    state = (state + 0x6d2b79f5) >>> 0;
    let value = Math.imul(state ^ (state >>> 15), state | 1);
    value ^= value + Math.imul(value ^ (value >>> 7), value | 61);
    return ((value ^ (value >>> 14)) >>> 0) / 0x100000000;
  };
}

export function shuffle(items, random) {
  for (let i = items.length - 1; i > 0; i--) {
    const other = Math.floor(random() * (i + 1));
    [items[i], items[other]] = [items[other], items[i]];
  }
  return items;
}

export function makeSamples(seed = DEFAULT_SEED) {
  const random = randomGenerator(seed);
  const block = Uint8Array.from({ length: 1024 }, () => Math.floor(random() * 256));
  const repeat = new Uint8Array(SAMPLE_SIZE);
  for (let offset = 0; offset < repeat.length; offset += block.length) repeat.set(block, offset);

  return {
    zeros: new Uint8Array(SAMPLE_SIZE),
    repeat,
    shuffled: shuffle(repeat.slice(), random),
    noise: Uint8Array.from({ length: SAMPLE_SIZE }, () => Math.floor(random() * 256)),
  };
}

// A miniature greedy LZ77 model for the short strings on the theory panel.
export function findTokens(input) {
  const tokens = [];
  let start = 0;
  while (start < input.length) {
    let length = 0;
    let distance = 0;
    for (let back = 1; back <= start; back++) {
      let match = 0;
      while (start + match < input.length && input[start + match] === input[start + match - back]) match++;
      if (match >= 3 && match > length) {
        length = match;
        distance = back;
      }
    }
    if (distance) {
      tokens.push({ start, length, distance, symbol: `⟨${length}, ${distance}⟩` });
      start += length;
    } else {
      tokens.push({ start, length: 1, symbol: input[start] });
      start++;
    }
  }
  return tokens;
}

export function makeHuffmanCodes(tokens) {
  const frequencies = new Map();
  for (const { symbol } of tokens) frequencies.set(symbol, (frequencies.get(symbol) ?? 0) + 1);
  const nodes = [...frequencies].map(([symbol, count]) => ({ symbol, count }));
  while (nodes.length > 1) {
    nodes.sort((a, b) => a.count - b.count);
    const [left, right] = nodes.splice(0, 2);
    nodes.push({ count: left.count + right.count, left, right });
  }
  const codes = [];
  function read(node, bits) {
    if (node.symbol !== undefined) codes.push({ ...node, bits: bits || '0' });
    else {
      read(node.left, bits + '0');
      read(node.right, bits + '1');
    }
  }
  read(nodes[0], '');
  return codes.sort((a, b) => b.count - a.count);
}
