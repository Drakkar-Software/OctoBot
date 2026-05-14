import React, {useEffect, useState, type ReactNode} from 'react';
import Translate, {translate} from '@docusaurus/Translate';
import styles from './LiveProof.module.css';

/*
 * Page-local hero visual — a compact order book that toggles between a
 * "without market maker" baseline and a "with OctoBot" live state, lighting
 * up tighter spreads and deeper books. Bespoke timed state machine, kept with
 * the /market-making page.
 */

type State = 'off' | 'on';

interface Row {
  bidPx: string;
  bidSz: string;
  bidMy: string;
  askPx: string;
  askSz: string;
  askMy: string;
  w: number;
}

const MID = 1.2841;

function genRows(spreadPct: number, depthMul: number, sparse: boolean, our: boolean): Row[] {
  const half = (MID * spreadPct) / 2;
  const rows: Row[] = [];
  for (let i = 0; i < 4; i++) {
    const step = (i + 1) * MID * (sparse ? 0.005 : 0.0008);
    const baseSize = depthMul * (90000 - i * 14000);
    const size = Math.max(600, Math.round(baseSize));
    const my = our ? Math.round(size * 0.86) : null;
    const baseW = 92 - i * 16;
    rows.push({
      bidPx: (MID - half - step).toFixed(4),
      askPx: (MID + half + step).toFixed(4),
      bidSz: size.toLocaleString(),
      askSz: size.toLocaleString(),
      bidMy: my ? my.toLocaleString() : '—',
      askMy: my ? my.toLocaleString() : '—',
      w: Math.max(6, Math.min(98, baseW * Math.min(1, depthMul * 1.2))),
    });
  }
  return rows;
}

const STATES: Record<
  State,
  {tag: string; foot: string; spread: string; depth: string; fill: string; rows: Row[]}
> = {
  off: {
    tag: translate({
      id: 'pages.marketMaking.liveProof.off.tag',
      message: 'Without market maker',
      description: 'Live proof state tag',
    }),
    foot: translate({
      id: 'pages.marketMaking.liveProof.off.foot',
      message: 'Snapshot · pre-launch baseline',
      description: 'Live proof state footnote',
    }),
    spread: '2.41%',
    depth: '€4.1k',
    fill: '6m 12s',
    rows: genRows(0.024, 0.05, true, false),
  },
  on: {
    tag: translate({
      id: 'pages.marketMaking.liveProof.on.tag',
      message: 'Live · with OctoBot MM',
      description: 'Live proof state tag',
    }),
    foot: translate({
      id: 'pages.marketMaking.liveProof.on.foot',
      message: 'Live · 340 quotes / sec · 99.97% uptime',
      description: 'Live proof state footnote',
    }),
    spread: '0.05%',
    depth: '€180k',
    fill: '0.4s',
    rows: genRows(0.0005, 2.2, false, true),
  },
};

export default function LiveProof(): ReactNode {
  const [state, setState] = useState<State>('off');

  useEffect(() => {
    const delay = state === 'off' ? 2400 : 4800;
    const timer = window.setTimeout(
      () => setState((s) => (s === 'off' ? 'on' : 'off')),
      delay,
    );
    return () => window.clearTimeout(timer);
  }, [state]);

  const data = STATES[state];

  return (
    <div className={`ng-card-hero ${styles.card}`} data-state={state}>
      <div className={styles.head}>
        <span className={styles.tag}>
          <span className={styles.tagDot} />
          {data.tag}
        </span>
        <span className={styles.pair}>
          <b>YOUR/USDT</b> · Binance Spot
        </span>
      </div>

      <div className={styles.stats}>
        {[
          {
            l: translate({
              id: 'pages.marketMaking.liveProof.stat.spread.label',
              message: 'Spread',
              description: 'Live proof stat label',
            }),
            v: data.spread,
            d: translate({
              id: 'pages.marketMaking.liveProof.stat.spread.delta',
              message: '↓ 98% tighter',
              description: 'Live proof stat delta',
            }),
          },
          {
            l: translate({
              id: 'pages.marketMaking.liveProof.stat.depth.label',
              message: 'Depth ±2%',
              description: 'Live proof stat label',
            }),
            v: data.depth,
            d: translate({
              id: 'pages.marketMaking.liveProof.stat.depth.delta',
              message: '↑ 44× deeper',
              description: 'Live proof stat delta',
            }),
          },
          {
            l: translate({
              id: 'pages.marketMaking.liveProof.stat.fill.label',
              message: 'Time to fill 10k',
              description: 'Live proof stat label',
            }),
            v: data.fill,
            d: translate({
              id: 'pages.marketMaking.liveProof.stat.fill.delta',
              message: '↓ 900× faster',
              description: 'Live proof stat delta',
            }),
          },
        ].map((stat) => (
          <div key={stat.l} className={styles.stat}>
            <div className={styles.statLabel}>{stat.l}</div>
            <div className={styles.statValue}>{stat.v}</div>
            <div className={styles.statDelta}>{stat.d}</div>
          </div>
        ))}
      </div>

      <div className={styles.book}>
        <div className={styles.bookCol}>
          {data.rows.map((row, i) => (
            <div key={i} className={styles.row} style={{'--w': `${row.w}%`} as React.CSSProperties}>
              <span className={styles.bidPx}>{row.bidPx}</span>
              <span className={styles.sz}>{row.bidSz}</span>
              <span className={styles.my}>{row.bidMy}</span>
            </div>
          ))}
        </div>
        <div className={styles.bookCol}>
          {data.rows.map((row, i) => (
            <div
              key={i}
              className={`${styles.row} ${styles.ask}`}
              style={{'--w': `${row.w}%`} as React.CSSProperties}>
              <span className={styles.askPx}>{row.askPx}</span>
              <span className={styles.sz}>{row.askSz}</span>
              <span className={styles.my}>{row.askMy}</span>
            </div>
          ))}
        </div>
      </div>

      <div className={styles.footnote}>
        <span>{data.foot}</span>
        <button
          type="button"
          className={styles.toggle}
          onClick={() => setState('off')}>
          <Translate
            id="pages.marketMaking.liveProof.replay"
            description="Live proof replay button">
            Replay ↻
          </Translate>
        </button>
      </div>
    </div>
  );
}
