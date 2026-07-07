import { useEffect, useRef, useState } from 'react'
import { createChart, LineSeries, LineStyle, CrosshairMode } from 'lightweight-charts'
import { CHART_COLORS } from '../lib/chartColors.js'
import './LightweightChart.css'

export default function LightweightChart({ rows, unit }) {
  const containerRef = useRef(null)
  const chartRef = useRef(null)
  const seriesRef = useRef({})
  const [tooltip, setTooltip] = useState(null)

  useEffect(() => {
    const container = containerRef.current
    if (!container) return undefined

    const chart = createChart(container, {
      autoSize: true,
      layout: {
        background: { color: 'transparent' },
        textColor: CHART_COLORS.muted,
        fontFamily: "'Space Grotesk', system-ui, sans-serif",
      },
      grid: {
        vertLines: { color: CHART_COLORS.border },
        horzLines: { color: CHART_COLORS.border },
      },
      crosshair: { mode: CrosshairMode.Normal },
      rightPriceScale: { borderColor: CHART_COLORS.border },
      timeScale: { borderColor: CHART_COLORS.border },
    })

    seriesRef.current.upper = chart.addSeries(LineSeries, {
      color: CHART_COLORS.short, lineWidth: 1, lineStyle: LineStyle.Dotted, priceLineVisible: false, lastValueVisible: false,
    })
    seriesRef.current.lower = chart.addSeries(LineSeries, {
      color: CHART_COLORS.long, lineWidth: 1, lineStyle: LineStyle.Dotted, priceLineVisible: false, lastValueVisible: false,
    })
    seriesRef.current.macro = chart.addSeries(LineSeries, {
      color: CHART_COLORS.muted, lineWidth: 1, priceLineVisible: false, lastValueVisible: false,
    })
    seriesRef.current.baseline = chart.addSeries(LineSeries, {
      color: CHART_COLORS.signal, lineWidth: 1, lineStyle: LineStyle.Dashed, priceLineVisible: false, lastValueVisible: false,
    })
    seriesRef.current.price = chart.addSeries(LineSeries, {
      color: CHART_COLORS.bullion, lineWidth: 3, priceLineVisible: false,
    })

    chart.subscribeCrosshairMove((param) => {
      if (!param.time || !param.point) {
        setTooltip(null)
        return
      }
      const priceData = param.seriesData.get(seriesRef.current.price)
      const baselineData = param.seriesData.get(seriesRef.current.baseline)
      const upperData = param.seriesData.get(seriesRef.current.upper)
      const lowerData = param.seriesData.get(seriesRef.current.lower)
      const macroData = param.seriesData.get(seriesRef.current.macro)
      if (!priceData) {
        setTooltip(null)
        return
      }
      setTooltip({
        x: param.point.x,
        y: param.point.y,
        date: param.time,
        price: priceData.value,
        baseline: baselineData?.value,
        upper: upperData?.value,
        lower: lowerData?.value,
        macro: macroData?.value,
      })
    })

    chartRef.current = chart
    return () => {
      chart.remove()
      chartRef.current = null
      seriesRef.current = {}
    }
  }, [])

  useEffect(() => {
    if (!rows || !seriesRef.current.price) return
    seriesRef.current.price.setData(rows.map((r) => ({ time: r.date, value: r.price })))
    seriesRef.current.baseline.setData(rows.map((r) => ({ time: r.date, value: r.baseline })))
    seriesRef.current.upper.setData(rows.map((r) => ({ time: r.date, value: r.upper })))
    seriesRef.current.lower.setData(rows.map((r) => ({ time: r.date, value: r.lower })))
    seriesRef.current.macro.setData(rows.map((r) => ({ time: r.date, value: r.macro })))
    chartRef.current?.timeScale().fitContent()
  }, [rows])

  return (
    <div className="lw-chart-wrap">
      <div ref={containerRef} className="lw-chart-container" />
      {tooltip && (
        <div
          className="lw-chart-tooltip"
          style={{
            left: Math.min(tooltip.x + 12, (containerRef.current?.clientWidth || 300) - 140),
            top: Math.max(tooltip.y - 8, 4),
          }}
        >
          <div className="lw-chart-tooltip-date">{tooltip.date}</div>
          <div className="lw-chart-tooltip-row" style={{ color: CHART_COLORS.bullion }}>
            Price ${tooltip.price?.toLocaleString()}{unit}
          </div>
          {tooltip.baseline != null && (
            <div className="lw-chart-tooltip-row" style={{ color: CHART_COLORS.signal }}>
              20 EMA ${tooltip.baseline.toLocaleString()}
            </div>
          )}
          {tooltip.macro != null && (
            <div className="lw-chart-tooltip-row" style={{ color: CHART_COLORS.muted }}>
              200 EMA ${tooltip.macro.toLocaleString()}
            </div>
          )}
          {tooltip.upper != null && (
            <div className="lw-chart-tooltip-row" style={{ color: CHART_COLORS.short }}>
              Upper ${tooltip.upper.toLocaleString()}
            </div>
          )}
          {tooltip.lower != null && (
            <div className="lw-chart-tooltip-row" style={{ color: CHART_COLORS.long }}>
              Lower ${tooltip.lower.toLocaleString()}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
