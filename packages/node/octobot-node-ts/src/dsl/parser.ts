import { DslParseError } from "../errors.js";

export interface ParsedDsl {
  keyword: string;
  args: (string | number)[];
}

export function parseDsl(source: string): ParsedDsl {
  const s = source.trim();
  const parenIdx = s.indexOf("(");
  if (parenIdx === -1) throw new DslParseError(source, 'missing "("');
  if (!s.endsWith(")")) throw new DslParseError(source, 'must end with ")"');

  const keyword = s.slice(0, parenIdx).trim();
  if (!/^[A-Za-z_][A-Za-z0-9_]*$/.test(keyword)) {
    throw new DslParseError(source, `invalid keyword "${keyword}"`);
  }

  const argsStr = s.slice(parenIdx + 1, -1).trim();
  if (!argsStr) return { keyword, args: [] };

  return { keyword, args: splitArgs(source, argsStr) };
}

function splitArgs(source: string, s: string): (string | number)[] {
  const parts: string[] = [];
  let start = 0;
  let inQ: string | null = null;

  for (let i = 0; i < s.length; i++) {
    const c = s[i];
    if (inQ) {
      if (c === inQ) inQ = null;
    } else if (c === '"' || c === "'") {
      inQ = c;
    } else if (c === ",") {
      parts.push(s.slice(start, i));
      start = i + 1;
    }
  }
  if (inQ) throw new DslParseError(source, "unterminated string");
  parts.push(s.slice(start));

  return parts.map((p, idx) => {
    const raw = p.trim();
    if (!raw) throw new DslParseError(source, `empty argument at position ${idx}`);
    if ((raw.startsWith('"') && raw.endsWith('"')) || (raw.startsWith("'") && raw.endsWith("'"))) {
      return raw.slice(1, -1);
    }
    const num = Number(raw);
    if (!isNaN(num)) return num;
    if (raw.includes("(") || raw.includes(")")) {
      throw new DslParseError(source, `nested calls not supported: "${raw}"`);
    }
    return raw;
  });
}
