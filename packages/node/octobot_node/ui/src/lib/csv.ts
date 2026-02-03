export interface CSVRow {
  name: string;
  content: string;
  type: string;
  metadata?: string;
}

const COLUMN_NAME = "name";
const COLUMN_CONTENT = "content";
const COLUMN_TYPE = "type";
const COLUMN_METADATA = "metadata";

/**
 * List of column names that are required to be present in the CSV header.
 * Rows missing any of these required keys will be skipped.
 */
const REQUIRED_KEYS = [COLUMN_NAME, COLUMN_TYPE];

/**
 * List of column names that should be extracted separately and kept outside of content.
 * These columns will be available as KEY=VALUE pairs.
 * Each key should be present in the CSVRow interface and added to the `processRow` return value.
 */
const KEYS_OUTSIDE_CONTENT = [COLUMN_NAME, COLUMN_TYPE, COLUMN_METADATA];

function parseCSVLine(line: string): Array<string> {
  const values: Array<string> = new Array<string>();
  let current = "";
  let inQuotes = false;

  for (let i = 0; i < line.length; i++) {
    const char = line[i];
    if (char === '"') {
      // Check if this is an escaped quote ("" inside quoted field)
      if (inQuotes && i + 1 < line.length && line[i + 1] === '"') {
        // Escaped quote: add a single quote and skip the next character
        current += '"';
        i++; // Skip the next quote
      } else {
        // Toggle quote state
        inQuotes = !inQuotes;
      }
    } else if (char === "," && !inQuotes) {
      values.push(current.trim());
      current = "";
    } else {
      current += char;
    }
  }
  values.push(current.trim());
  return values;
}

function parseHeader(headerLine: string): Array<string> | null {
  const columnNames = parseCSVLine(headerLine)
    .map((col) => col.trim())
    .filter((col) => col !== "");
  if (columnNames.length === 0) {
    return null;
  }
  return columnNames;
}

function findColumnIndices(
  columnNames: Array<string>,
  keys: Array<string>
): Map<number, string> {
  const indices: Map<number, string> = new Map<number, string>();
  for (const key of keys) {
    const index = columnNames.findIndex(
      (col) => col.toLowerCase() === key.toLowerCase()
    );
    if (index !== -1) {
      indices.set(index, key);
    }
  }
  return indices;
}

function validateRequiredKeys(
  columnNames: Array<string>
): Map<number, string> | null {
  const requiredKeysIndices: Map<number, string> = new Map<number, string>();
  for (const key of REQUIRED_KEYS) {
    const index = columnNames.findIndex(
      (col) => col.toLowerCase() === key.toLowerCase()
    );
    if (index === -1) {
      return null;
    }
    requiredKeysIndices.set(index, key);
  }
  return requiredKeysIndices;
}

function findContentColumnIndex(columnNames: Array<string>): number {
  return columnNames.findIndex(
    (col) => col.toLowerCase() === COLUMN_CONTENT.toLowerCase()
  );
}

function extractKeysOutsideContent(
  values: Array<string>,
  keysOutsideContentIndices: Map<number, string>
): Map<string, string> {
  const keysOutsideContentValues: Map<string, string> = new Map<
    string,
    string
  >();
  for (const [index, key] of keysOutsideContentIndices) {
    const value = values[index]?.trim();
    if (value !== undefined) {
      keysOutsideContentValues.set(key, value);
    }
  }
  return keysOutsideContentValues;
}

function buildContent(
  values: Array<string>,
  columnNames: Array<string>,
  keysOutsideContentIndices: Map<number, string>,
  contentColumnIndex: number
): string {
  const contentObject: Record<string, unknown> = {};
  
  // Add all columns (except keys outside content and the content column itself) to the JSON object
  for (let i = 0; i < columnNames.length && i < values.length; i++) {
    if (!keysOutsideContentIndices.has(i) && i !== contentColumnIndex) {
      const value = values[i]?.trim();
      if (value !== undefined && value !== "") {
        const columnName = columnNames[i];
        const upperKey = columnName.toUpperCase();
        
        // Try to parse as JSON, otherwise use as string
        try {
          const parsedValue = JSON.parse(value);
          contentObject[upperKey] = parsedValue;
        } catch {
          // If not valid JSON, use as string
          contentObject[upperKey] = value;
        }
      }
    }
  }

  // If there's a content column, try to parse it as JSON and merge it
  if (contentColumnIndex !== -1) {
    const contentColumnValue = values[contentColumnIndex]?.trim();
    if (contentColumnValue) {
      try {
        const parsedContent = JSON.parse(contentColumnValue);
        // Merge the parsed content into the content object
        if (typeof parsedContent === "object" && parsedContent !== null && !Array.isArray(parsedContent)) {
          Object.assign(contentObject, parsedContent);
        } else {
          // If content is not an object, add it as a special key
          contentObject["CONTENT"] = parsedContent;
        }
      } catch {
        // If not valid JSON, add as string
        contentObject["CONTENT"] = contentColumnValue;
      }
    }
  }
  
  return JSON.stringify(contentObject);
}

function validateRowHasRequiredKeys(
  values: Array<string>,
  requiredKeysIndices: Map<number, string>
): boolean {
  for (const [index] of requiredKeysIndices) {
    const value = values[index]?.trim();
    if (!value) {
      return false;
    }
  }
  return true;
}

function processRow(
  line: string,
  columnNames: Array<string>,
  requiredKeysIndices: Map<number, string>,
  keysOutsideContentIndices: Map<number, string>,
  contentColumnIndex: number
): CSVRow | null {
  if (!line.trim()) {
    throw new Error("Empty row found in the CSV file");
  }

  const values = parseCSVLine(line);

  if (!validateRowHasRequiredKeys(values, requiredKeysIndices)) {
    throw new Error("Required keys not found in the CSV row");
  }

  const keysOutsideContentValues = extractKeysOutsideContent(
    values,
    keysOutsideContentIndices
  );
  const hasMetadata = keysOutsideContentValues.has(COLUMN_METADATA);
  
  let finalContent: string;
  if (hasMetadata && contentColumnIndex !== -1) {
    // For encrypted CSVs, pass through content as-is (base64 string)
    finalContent = values[contentColumnIndex]?.trim() || "";
  } else {
    // For non-encrypted CSVs, build JSON content from columns
    finalContent = buildContent(
      values,
      columnNames,
      keysOutsideContentIndices,
      contentColumnIndex
    );
  }

  return {
    name: keysOutsideContentValues.get(COLUMN_NAME) || "",
    content: finalContent,
    type: keysOutsideContentValues.get(COLUMN_TYPE) || "",
    metadata: keysOutsideContentValues.get(COLUMN_METADATA) || "",
  };
}

export function parseCSV(csvText: string): Array<CSVRow> {
  const lines = csvText.trim().split("\n");
  if (lines.length === 0 || lines.length === 1) {
    throw new Error("No lines found in the CSV file");
  }

  const headerLine = lines[0];
  const columnNames = parseHeader(headerLine);
  if (columnNames === null) {
    throw new Error("No column names found in the CSV header");
  }

  const requiredKeysIndices = validateRequiredKeys(columnNames);
  if (requiredKeysIndices === null) {
    throw new Error("Required keys not found in the CSV header");
  }

  const keysOutsideContentIndices = findColumnIndices(
    columnNames,
    KEYS_OUTSIDE_CONTENT
  );
  const contentColumnIndex = findContentColumnIndex(columnNames);

  const dataLines = lines.slice(1);
  const rows: Array<CSVRow> = new Array<CSVRow>();

  for (const line of dataLines) {
    try {
      const row = processRow(
        line,
        columnNames,
        requiredKeysIndices,
        keysOutsideContentIndices,
        contentColumnIndex
      );
      if (row !== null) {
        rows.push(row);
      }
    } catch (error) {
      console.error(`Failed to process CSV row: ${error instanceof Error ? error.message : "Unknown error"}`)
    }
  }

  return rows;
}

export function isValidCSVFile(file: File): boolean {
  return file.name.endsWith(".csv");
}

export async function parseCSVFile(file: File): Promise<CSVRow[]> {
  if (!isValidCSVFile(file)) {
    throw new Error("File must be a CSV file");
  }

  try {
    const text = await file.text();
    return parseCSV(text);
  } catch (error) {
    throw new Error(
      `Failed to read CSV file: ${error instanceof Error ? error.message : "Unknown error"}`
    );
  }
}

export function escapeCSVValue(value: unknown): string {
  if (value === null || value === undefined) {
    return "";
  }
  
  const stringValue = typeof value === "object" 
    ? JSON.stringify(value) 
    : String(value);
  
  // If value contains comma, quote, or newline, wrap in quotes and escape quotes
  if (stringValue.includes(",") || stringValue.includes('"') || stringValue.includes("\n")) {
    return `"${stringValue.replace(/"/g, '""')}"`;
  }
  
  return stringValue;
}

export function generateCSV(headers: string[], rows: unknown[][]): string {
  const csvRows: string[] = [];
  
  csvRows.push(headers.map(escapeCSVValue).join(","));
  
  for (const row of rows) {
    csvRows.push(row.map(escapeCSVValue).join(","));
  }
  
  return csvRows.join("\n");
}

export function downloadCSV(csvString: string, filename: string): void {
  const blob = new Blob([csvString], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `${filename}.csv`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}
