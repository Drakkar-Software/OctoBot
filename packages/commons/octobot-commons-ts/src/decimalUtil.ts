import Decimal from "decimal.js";

export type DecimalLike = Decimal | string | number;

export const ZERO = new Decimal(0);
export const ONE = new Decimal(1);

export function toDecimal(value: DecimalLike | null | undefined): Decimal {
  if (value === null || value === undefined || value === "") return ZERO;
  if (value instanceof Decimal) return value;
  return new Decimal(value);
}

export function tryDecimal(value: DecimalLike | null | undefined): Decimal | null {
  if (value === null || value === undefined || value === "") return null;
  try {
    return value instanceof Decimal ? value : new Decimal(value);
  } catch {
    return null;
  }
}

export function decimalToFloat(value: Decimal | null | undefined): number {
  if (value === null || value === undefined) return Number.NaN;
  return value.toNumber();
}

export function isFiniteDecimal(value: Decimal | null | undefined): boolean {
  return !!value && value.isFinite();
}

export function decimalEquals(a: Decimal, b: Decimal): boolean {
  return a.eq(b);
}

export function isMissing(value: Decimal | null | undefined): boolean {
  if (value === null || value === undefined) return true;
  return value.isNaN();
}

export { Decimal };
