import React, {type ReactNode} from 'react';
import Translate, {translate} from '@docusaurus/Translate';
import GlassCard from '@site/src/components/GlassCard';
import styles from './ReportingDashboard.module.css';

/*
 * Page-local reporting console — a static ops dashboard mockup (identity row,
 * four KPI tiles with sparklines, a depth chart). Bespoke composition, kept
 * with the /market-making page.
 */

const KPIS = [
  {
    label: translate({
      id: 'pages.marketMaking.reporting.kpi.spread.label',
      message: 'Median spread',
      description: 'Reporting dashboard KPI label',
    }),
    value: '0.06%',
    delta: translate({
      id: 'pages.marketMaking.reporting.kpi.spread.delta',
      message: '↓ tighter',
      description: 'Reporting dashboard KPI delta',
    }),
    spark: '0,16 8,14 16,15 24,11 32,12 40,8 48,9 56,6',
    color: 'var(--ng-pos)',
  },
  {
    label: translate({
      id: 'pages.marketMaking.reporting.kpi.depth.label',
      message: 'Depth ±2%',
      description: 'Reporting dashboard KPI label',
    }),
    value: '$1.42M',
    delta: translate({
      id: 'pages.marketMaking.reporting.kpi.depth.delta',
      message: '↑ deeper',
      description: 'Reporting dashboard KPI delta',
    }),
    spark: '0,18 8,16 16,12 24,13 32,9 40,10 48,5 56,4',
    color: 'var(--ng-frost)',
  },
  {
    label: translate({
      id: 'pages.marketMaking.reporting.kpi.volume.label',
      message: 'Volume share',
      description: 'Reporting dashboard KPI label',
    }),
    value: '38%',
    delta: translate({
      id: 'pages.marketMaking.reporting.kpi.volume.delta',
      message: '↑ higher',
      description: 'Reporting dashboard KPI delta',
    }),
    spark: '0,14 8,15 16,12 24,13 32,10 40,11 48,7 56,8',
    color: 'var(--ng-turquoise)',
  },
  {
    label: translate({
      id: 'pages.marketMaking.reporting.kpi.uptime.label',
      message: 'Uptime',
      description: 'Reporting dashboard KPI label',
    }),
    value: '99.97%',
    delta: translate({
      id: 'pages.marketMaking.reporting.kpi.uptime.delta',
      message: 'stable',
      description: 'Reporting dashboard KPI delta',
    }),
    spark: '0,4 8,4 16,4 24,4 32,5 40,4 48,4 56,4',
    color: 'var(--ng-pos)',
    stable: true,
  },
];

const DAYS = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN'];

export default function ReportingDashboard(): ReactNode {
  return (
    <GlassCard variant="strong" padded={false} className={styles.rpt}>
      <div className={styles.head}>
        <div className={styles.id}>
          <div className={styles.mark}>Y</div>
          <div>
            <h4 className={styles.idTitle}>YOURTOKEN / USDT</h4>
            <div className={styles.idSub}>
              <span className={styles.live} />
              <Translate
                id="pages.marketMaking.reporting.streaming"
                description="Reporting dashboard streaming status">
                streaming · 4 venues
              </Translate>
            </div>
          </div>
        </div>
      </div>

      <div className={styles.kpis}>
        {KPIS.map((kpi) => (
          <div key={kpi.label} className={styles.kpi}>
            <div className={styles.kpiLabel}>{kpi.label}</div>
            <div
              className={styles.kpiValue}
              style={kpi.stable ? {color: 'var(--ng-pos)'} : undefined}>
              {kpi.value}
            </div>
            <div className={styles.kpiDelta}>{kpi.delta}</div>
            <svg className={styles.spark} width="56" height="22" viewBox="0 0 56 22">
              <polyline
                points={kpi.spark}
                fill="none"
                stroke={kpi.color}
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </div>
        ))}
      </div>

      <div className={styles.chart}>
        <div className={styles.chartHead}>
          <span className={styles.chartTitle}>
            <Translate
              id="pages.marketMaking.reporting.chartTitle"
              description="Reporting dashboard chart title">
              Depth ±2% · 7 days
            </Translate>
          </span>
          <span className={styles.legend}>
            <i />
            <Translate
              id="pages.marketMaking.reporting.legend"
              description="Reporting dashboard chart legend">
              Depth
            </Translate>
          </span>
        </div>
        <div className={styles.canvas}>
          <svg viewBox="0 0 400 200" preserveAspectRatio="none">
            <defs>
              <linearGradient id="mmRptDepth" x1="0" x2="0" y1="0" y2="1">
                <stop offset="0%" stopColor="#85d6d7" stopOpacity="0.45" />
                <stop offset="100%" stopColor="#85d6d7" stopOpacity="0" />
              </linearGradient>
            </defs>
            <line x1="0" y1="50" x2="400" y2="50" stroke="rgba(255,255,255,0.05)" strokeDasharray="3 5" />
            <line x1="0" y1="100" x2="400" y2="100" stroke="rgba(255,255,255,0.05)" strokeDasharray="3 5" />
            <line x1="0" y1="150" x2="400" y2="150" stroke="rgba(255,255,255,0.05)" strokeDasharray="3 5" />
            <path
              d="M0,150 C30,140 60,148 90,128 C120,112 150,118 180,98 C210,82 240,90 270,68 C300,52 330,60 360,42 L400,34 L400,200 L0,200 Z"
              fill="url(#mmRptDepth)"
            />
            <path
              d="M0,150 C30,140 60,148 90,128 C120,112 150,118 180,98 C210,82 240,90 270,68 C300,52 330,60 360,42 L400,34"
              stroke="#85d6d7"
              strokeWidth="2"
              fill="none"
            />
            <circle cx="270" cy="68" r="4" fill="#85d6d7" />
            <circle cx="270" cy="68" r="8" fill="none" stroke="#85d6d7" strokeOpacity="0.4" />
          </svg>
          <div className={styles.pin} style={{left: '67.5%', top: '28%'}}>
            <Translate
              id="pages.marketMaking.reporting.pin"
              description="Reporting dashboard chart pin label">
              Thu · $1.78M peak
            </Translate>
          </div>
        </div>
        <div className={styles.xAxis}>
          {DAYS.map((day) => (
            <span key={day}>{day}</span>
          ))}
        </div>
      </div>
    </GlassCard>
  );
}
