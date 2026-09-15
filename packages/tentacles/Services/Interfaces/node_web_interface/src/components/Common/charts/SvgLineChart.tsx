import { useLayoutEffect, useMemo, useRef, useState, type ReactNode } from "react"
import { createPortal } from "react-dom"

import {
  buildLinearTicks,
  buildLinePath,
  domainFromPoints,
  findNearestPointIndex,
  formatDefaultYTick,
  getChartTooltipViewportPosition,
  scaleLinear,
  type ChartTooltipViewportPosition,
  type SvgLineChartPoint,
} from "@/lib/charts/svg-line-chart"

const CHART_PADDING = {
  top: 12,
  right: 12,
  bottom: 24,
  left: 48,
}

export type SvgLineChartProps = {
  points: SvgLineChartPoint[]
  width?: number
  height?: number
  ariaLabel?: string
  renderTooltip?: (point: SvgLineChartPoint, index: number) => ReactNode
  emptyMessage?: string
  formatYTick?: (value: number) => string
}

type TooltipState = {
  index: number
}

export function SvgLineChart({
  points,
  width = 640,
  height = 220,
  ariaLabel = "Line chart",
  renderTooltip,
  emptyMessage = "No data",
  formatYTick = formatDefaultYTick,
}: SvgLineChartProps) {
  const svgRef = useRef<SVGSVGElement>(null)
  const [tooltipState, setTooltipState] = useState<TooltipState | null>(null)
  const [tooltipPosition, setTooltipPosition] =
    useState<ChartTooltipViewportPosition | null>(null)

  const plotWidth = width - CHART_PADDING.left - CHART_PADDING.right
  const plotHeight = height - CHART_PADDING.top - CHART_PADDING.bottom

  const { path, scaledPoints, xScale, yScale, yTicks } = useMemo(() => {
    const xDomain = domainFromPoints(points, "x")
    const yDomain = domainFromPoints(points, "y")
    const computedXScale = scaleLinear(
      xDomain.min,
      xDomain.max,
      CHART_PADDING.left,
      CHART_PADDING.left + plotWidth,
    )
    const computedYScale = scaleLinear(
      yDomain.min,
      yDomain.max,
      CHART_PADDING.top + plotHeight,
      CHART_PADDING.top,
    )
    return {
      path: buildLinePath(points, computedXScale, computedYScale),
      scaledPoints: points.map((point) => ({
        x: computedXScale.toSvg(point.x),
        y: computedYScale.toSvg(point.y),
      })),
      xScale: computedXScale,
      yScale: computedYScale,
      yTicks: buildLinearTicks(yDomain.min, yDomain.max),
    }
  }, [points, plotHeight, plotWidth])

  const activePoint =
    tooltipState === null ? null : points[tooltipState.index]
  const activeScaledPoint =
    tooltipState === null ? null : scaledPoints[tooltipState.index]

  useLayoutEffect(() => {
    if (
      tooltipState === null ||
      activeScaledPoint === null ||
      svgRef.current === null
    ) {
      setTooltipPosition(null)
      return
    }
    const svgBounds = svgRef.current.getBoundingClientRect()
    setTooltipPosition(
      getChartTooltipViewportPosition(
        svgBounds,
        activeScaledPoint.x,
        activeScaledPoint.y,
        width,
        height,
      ),
    )
  }, [activeScaledPoint, height, tooltipState, width])

  if (points.length === 0) {
    return (
      <p className="text-sm text-muted-foreground py-6 text-center">
        {emptyMessage}
      </p>
    )
  }

  const updateTooltipFromClientPosition = (clientX: number) => {
    const svgElement = svgRef.current
    if (!svgElement) {
      return
    }
    const bounds = svgElement.getBoundingClientRect()
    const relativeX =
      ((clientX - bounds.left) / bounds.width) * width
    const dataX = xScale.min + ((relativeX - CHART_PADDING.left) / plotWidth) * (xScale.max - xScale.min)
    const nearestIndex = findNearestPointIndex(points, dataX)
    if (nearestIndex === null) {
      return
    }
    setTooltipState({ index: nearestIndex })
  }

  const tooltipContent =
    tooltipState !== null &&
    activePoint !== null &&
    renderTooltip?.(activePoint, tooltipState.index)

  return (
    <div className="relative">
      <svg
        ref={svgRef}
        viewBox={`0 0 ${width} ${height}`}
        className="w-full h-auto"
        role="img"
        aria-label={ariaLabel}
        onMouseLeave={() => setTooltipState(null)}
        onMouseMove={(event) =>
          updateTooltipFromClientPosition(event.clientX)
        }
      >
        {yTicks.map((tickValue) => {
          const tickY = yScale.toSvg(tickValue)
          return (
            <g key={tickValue}>
              <line
                x1={CHART_PADDING.left}
                x2={CHART_PADDING.left + plotWidth}
                y1={tickY}
                y2={tickY}
                className="stroke-border"
                strokeWidth={1}
                opacity={0.35}
              />
              <text
                x={CHART_PADDING.left - 8}
                y={tickY}
                textAnchor="end"
                dominantBaseline="middle"
                className="fill-muted-foreground text-[10px]"
              >
                {formatYTick(tickValue)}
              </text>
            </g>
          )
        })}
        <rect
          x={CHART_PADDING.left}
          y={CHART_PADDING.top}
          width={plotWidth}
          height={plotHeight}
          fill="transparent"
        />
        <path
          d={path}
          fill="none"
          stroke="currentColor"
          strokeWidth={2}
          className="text-primary"
        />
        {scaledPoints.map((scaledPoint, pointIndex) => (
          <circle
            key={`${points[pointIndex].x}-${pointIndex}`}
            cx={scaledPoint.x}
            cy={scaledPoint.y}
            r={tooltipState?.index === pointIndex ? 5 : 3}
            className="fill-primary"
          />
        ))}
      </svg>
      {tooltipContent &&
        tooltipPosition !== null &&
        createPortal(
          <div
            className="pointer-events-none fixed z-[200] rounded-md border bg-popover px-3 py-2 text-popover-foreground shadow-md text-xs"
            style={{
              left: tooltipPosition.left,
              top: tooltipPosition.top,
              transform: tooltipPosition.transform,
            }}
          >
            {tooltipContent}
          </div>,
          document.body,
        )}
    </div>
  )
}
