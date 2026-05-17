const HTTP_IMPORT = /^import \{ HttpFile \} from '\.\.\/http\/http';\n/m;
const DATE_FIELD = /^(\s*'[^']+'?\??:\s*)Date\b/gm;
const ENUM_BLOCK = /export enum (\w+) \{([^}]+)\}/g;

export function stripHttpImport(src) {
  return src.replace(HTTP_IMPORT, "");
}

export function dateFieldsToString(src) {
  return src.replace(DATE_FIELD, "$1string");
}

export function enumBlockToUnion(src) {
  return src.replace(ENUM_BLOCK, (whole, name, body) => {
    const union = body
      .split(",")
      .map((line) => {
        const match = line.match(/=\s*'([^']*)'/);
        return match ? `'${match[1]}'` : null;
      })
      .filter(Boolean)
      .join(" | ");
    return union ? `export type ${name} = ${union}` : whole;
  });
}

export function narrowDiscriminatorField(src, field, literal) {
  const pattern = new RegExp(`(['\"]${field}['\"]\\??:\\s*)[A-Za-z_]\\w*(?=\\s*[;,])`, "g");
  return src.replace(pattern, `$1'${literal}'`);
}

export function collectVariantNarrowings(openapi) {
  const result = new Map();
  const schemas = openapi?.components?.schemas;
  if (!schemas) return result;
  for (const [name, schema] of Object.entries(schemas)) {
    const props = schema?.properties;
    if (!props) continue;
    for (const [propName, prop] of Object.entries(props)) {
      if (!prop || typeof prop !== "object") continue;
      if (typeof prop.$ref !== "string") continue;
      if (typeof prop.description !== "string") continue;
      const list = result.get(name) ?? [];
      list.push({ field: propName, literal: prop.description });
      result.set(name, list);
    }
  }
  return result;
}
