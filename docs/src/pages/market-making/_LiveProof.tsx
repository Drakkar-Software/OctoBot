import React, {useEffect, useState, type ReactNode} from 'react';
import GlassCard from '@site/src/components/GlassCard';
import styles from './_LiveProof.module.css';

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
    tag: 'Without market maker',
    foot: 'Snapshot · pre-launch baseline',
    spread: '2.41%',
    depth: '€4.1k',
    fill: '6m 12s',
    rows: genRows(0.024, 0.05, true, false),
  },
  on: {
    tag: 'Live · with OctoBot MM',
    foot: 'Live · 340 quotes / sec · 99.97% uptime',
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
    <GlassCard variant="hero" padded={false} className={styles.card} data-state={state}>
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
          {l: 'Spread', v: data.spread, d: '↓ 98% tighter'},
          {l: 'Depth ±2%', v: data.depth, d: '↑ 44× deeper'},
          {l: 'Time to fill 10k', v: data.fill, d: '↓ 900× faster'},
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
          Replay ↻
        </button>
      </div>
    </GlassCard>
  );
}
