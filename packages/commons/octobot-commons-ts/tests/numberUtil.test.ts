import { describe, it, expect } from "vitest";
import { getDigitsCount, roundIntoMaxDigits } from "../src/numberUtil.js";

describe("numberUtil", () => {
  it("counts decimal digits", () => {
    expect(getDigitsCount(1.234)).toBe(3);
    expect(getDigitsCount(0.0001)).toBe(4);
    expect(getDigitsCount(1)).toBe(1);
    expect(getDigitsCount(0)).toBe(0);
  });

  it("rounds to N digits", () => {
    expect(roundIntoMaxDigits(1.23456, 2)).toBe(1.23);
    expect(roundIntoMaxDigits(1.235, 2)).toBe(1.24);
  });
});
