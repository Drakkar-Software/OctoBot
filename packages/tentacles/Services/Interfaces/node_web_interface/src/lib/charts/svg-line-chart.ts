export type SvgLineChartPoint = {
  x: number
  y: number
}

export type LinearScale = {
  min: number
  max: number
  toSvg: (value: number) => number
}

export function scaleLinear(
  domainMin: number,
  domainMax: number,
  rangeMin: number,
  rangeMax: number,
): LinearScale {
  const domainSpan = domainMax - domainMin
  const rangeSpan = rangeMax - rangeMin
  return {
    min: domainMin,
    max: domainMax,
    toSvg: (value: number) => {
      if (domainSpan === 0) {
        return (rangeMin + rangeMax) / 2
      }
      const ratio = (value - domainMin) / domainSpan
      return rangeMin + ratio * rangeSpan
    },
  }
}

export function buildLinePath(
  points: SvgLineChartPoint[],
  xScale: LinearScale,
  yScale: LinearScale,
): string {
  if (points.length === 0) {
    return ""
  }
  return points
    .map((point, index) => {
      const command = index === 0 ? "M" : "L"
      const svgX = xScale.toSvg(point.x)
      const svgY = yScale.toSvg(point.y)
      return `${command}${svgX},${svgY}`
    })
    .join(" ")
}

export function findNearestPointIndex(
  points: SvgLineChartPoint[],
  targetX: number,
): number | null {
  if (points.length === 0) {
    return null
  }
  let nearestIndex = 0
  let nearestDistance = Math.abs(points[0].x - targetX)
  for (let pointIndex = 1; pointIndex < points.length; pointIndex += 1) {
    const distance = Math.abs(points[pointIndex].x - targetX)
    if (distance < nearestDistance) {
      nearestDistance = distance
      nearestIndex = pointIndex
    }
  }
  return nearestIndex
}

export function domainFromPoints(
  points: SvgLineChartPoint[],
  axis: "x" | "y",
): { min: number; max: number } {
  if (points.length === 0) {
    return { min: 0, max: 1 }
  }
  const values = points.map((point) => (axis === "x" ? point.x : point.y))
  const min = Math.min(...values)
  const max = Math.max(...values)
  if (min === max) {
    const padding = axis === "x" ? 86_400_000 : Math.max(Math.abs(min) * 0.1, 1)
    return { min: min - padding, max: max + padding }
  }
  return { min, max }
}

export function buildLinearTicks(
  domainMin: number,
  domainMax: number,
  tickCount: number = 5,
): number[] {
  if (tickCount < 2) {
    return [domainMin, domainMax]
  }
  const domainSpan = domainMax - domainMin
  if (domainSpan === 0) {
    return [domainMin]
  }
  const rawStep = domainSpan / (tickCount - 1)
  const magnitude = 10 ** Math.floor(Math.log10(rawStep))
  const normalizedStep = rawStep / magnitude
  let niceStep = magnitude
  if (normalizedStep <= 1) {
    niceStep = magnitude
  } else if (normalizedStep <= 2) {
    niceStep = 2 * magnitude
  } else if (normalizedStep <= 5) {
    niceStep = 5 * magnitude
  } else {
    niceStep = 10 * magnitude
  }
  const niceMin = Math.floor(domainMin / niceStep) * niceStep
  const ticks: number[] = []
  for (let tickValue = niceMin; tickValue <= domainMax + niceStep * 0.5; tickValue += niceStep) {
    if (tickValue >= domainMin - niceStep * 0.5) {
      ticks.push(Number(tickValue.toPrecision(12)))
    }
  }
  return ticks.length > 0 ? ticks : [domainMin, domainMax]
}

export function formatDefaultYTick(value: number): string {
  return value.toLocaleString(undefined, {
    maximumFractionDigits: value >= 1000 ? 0 : 2,
  })
}

export type ChartTooltipViewportPosition = {
  left: number
  top: number
  transform?: string
}

export type SvgElementBounds = {
  left: number
  top: number
  width: number
  height: number
}

export function getChartTooltipViewportPosition(
  svgBounds: SvgElementBounds,
  scaledX: number,
  scaledY: number,
  viewBoxWidth: number,
  viewBoxHeight: number,
  tooltipOffset = 12,
  viewportWidth = typeof window === "undefined" ? Number.POSITIVE_INFINITY : window.innerWidth,
): ChartTooltipViewportPosition {
  const anchorLeft = svgBounds.left + (scaledX / viewBoxWidth) * svgBounds.width
  const anchorTop = svgBounds.top + (scaledY / viewBoxHeight) * svgBounds.height
  const estimatedTooltipWidth = 280
  const placeLeft =
    anchorLeft + tooltipOffset + estimatedTooltipWidth > viewportWidth
  return {
    left: placeLeft
      ? anchorLeft - tooltipOffset
      : anchorLeft + tooltipOffset,
    top: anchorTop + tooltipOffset,
    transform: placeLeft ? "translateX(-100%)" : undefined,
  }
}
