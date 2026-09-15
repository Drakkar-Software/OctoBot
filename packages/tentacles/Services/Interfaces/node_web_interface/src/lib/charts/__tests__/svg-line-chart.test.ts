import { describe, expect, it } from "vitest"

import {
  buildLinearTicks,
  buildLinePath,
  domainFromPoints,
  findNearestPointIndex,
  formatDefaultYTick,
  getChartTooltipViewportPosition,
  scaleLinear,
} from "@/lib/charts/svg-line-chart"

describe("scaleLinear", () => {
  it("maps values into the svg range", () => {
    const scale = scaleLinear(0, 100, 10, 110)
    expect(scale.toSvg(0)).toBe(10)
    expect(scale.toSvg(100)).toBe(110)
    expect(scale.toSvg(50)).toBe(60)
  })

  it("returns midpoint when domain span is zero", () => {
    const scale = scaleLinear(5, 5, 0, 200)
    expect(scale.toSvg(5)).toBe(100)
  })
})

describe("buildLinePath", () => {
  it("builds an svg path from scaled points", () => {
    const xScale = scaleLinear(0, 100, 0, 100)
    const yScale = scaleLinear(0, 100, 100, 0)
    const path = buildLinePath(
      [
        { x: 0, y: 0 },
        { x: 100, y: 100 },
      ],
      xScale,
      yScale,
    )
    expect(path).toBe("M0,100 L100,0")
  })
})

describe("findNearestPointIndex", () => {
  it("returns the closest point by x coordinate", () => {
    const points = [
      { x: 10, y: 1 },
      { x: 20, y: 2 },
      { x: 30, y: 3 },
    ]
    expect(findNearestPointIndex(points, 21)).toBe(1)
    expect(findNearestPointIndex(points, 8)).toBe(0)
  })
})

describe("domainFromPoints", () => {
  it("pads a flat y domain", () => {
    const domain = domainFromPoints([{ x: 1, y: 100 }], "y")
    expect(domain.min).toBeLessThan(100)
    expect(domain.max).toBeGreaterThan(100)
  })
})

describe("buildLinearTicks", () => {
  it("returns evenly spaced ticks across the domain", () => {
    const ticks = buildLinearTicks(0, 1000, 5)
    expect(ticks.length).toBeGreaterThanOrEqual(2)
    expect(ticks[0]).toBeLessThanOrEqual(0)
    expect(ticks[ticks.length - 1]).toBeGreaterThanOrEqual(1000)
  })
})

describe("formatDefaultYTick", () => {
  it("formats large values without decimals", () => {
    expect(formatDefaultYTick(1500)).toMatch(/1.500/)
  })
})

describe("getChartTooltipViewportPosition", () => {
  it("places the tooltip to the right of the anchor by default", () => {
    const position = getChartTooltipViewportPosition(
      { left: 100, top: 50, width: 400, height: 200 },
      320,
      110,
      640,
      220,
    )
    expect(position.left).toBeGreaterThan(100)
    expect(position.top).toBeGreaterThan(50)
  })
})
