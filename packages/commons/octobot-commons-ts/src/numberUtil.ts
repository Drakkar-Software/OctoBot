// Mirror of subset of octobot_commons.number_util.

/** Returns the number of digits after the decimal point. */
export function getDigitsCount(value: number | null | undefined): number {
  if (value === null || value === undefined) return 0;
  if (Number.isInteger(value)) return Number(value);
  const s = value.toString();
  if (s.includes("e-")) {
    const [, exp] = s.split("e-");
    return parseInt(exp, 10);
  }
  if (s.includes(".")) return s.split(".")[1].length;
  return 0;
}

/** Round a value to the given number of digits. */
export function roundIntoMaxDigits(value: number, maxDigits: number): number {
  const factor = 10 ** maxDigits;
  return Math.round(value * factor) / factor;
}

export function isNumeric(v: unknown): boolean {
  if (typeof v === "number") return !Number.isNaN(v);
  if (typeof v === "string") return !Number.isNaN(parseFloat(v));
  return false;
}
