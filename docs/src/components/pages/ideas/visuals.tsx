/**
 * Hero visuals for the SEO "ideas" pages.
 *
 * Each page picks a different one of these so pages built from the same
 * <IdeaPage> template still look distinct. They are deliberately static mocks
 * — illustrative, not live data — and lean entirely on the Neo Glass Dark
 * tokens via styles.module.css.
 */

import type {ReactNode} from 'react';
import GlassCard from '@site/src/components/GlassCard';
import styles from './styles.module.css';

function Shell({
  label,
  note,
  children,
}: {
  label: string;
  note?: string;
  children: ReactNode;
}): ReactNode {
  return (
    <GlassCard variant="hero" padded={false} className={styles.visual}>
      <div className={styles.visualHead}>
        <span className={styles.visualLabel}>{label}</span>
        {note ? <span className={styles.visualNote}>{note}</span> : null}
      </div>
      {children}
    </GlassCard>
  );
}

/** Bid/ask order book — market making, liquidity, designated-MM pages. */
export function LadderVisual({
  label,
  note,
  bids,
  asks,
  mid,
}: {
  label: string;
  note?: string;
  bids: {price: string; size: string; depth: number}[];
  asks: {price: string; size: string; depth: number}[];
  mid: string;
}): ReactNode {
  return (
    <Shell label={label} note={note}>
      <div className={styles.ladder}>
        {asks.map((r) => (
          <div
            key={r.price}
            className={`${styles.ladderRow} ${styles.ladderAsk}`}
            style={{'--depth': `${r.depth}%`} as React.CSSProperties}>
            <span>{r.price}</span>
            <span>{r.size}</span>
          </div>
        ))}
        <div className={styles.ladderMid}>{mid}</div>
        {bids.map((r) => (
          <div
            key={r.price}
            className={`${styles.ladderRow} ${styles.ladderBid}`}
            style={{'--depth': `${r.depth}%`} as React.CSSProperties}>
            <span>{r.price}</span>
            <span>{r.size}</span>
          </div>
        ))}
      </div>
    </Shell>
  );
}

/** Column chart with a P&L caption — grid trading, backtesting pages. */
export function BarsVisual({
  label,
  note,
  bars,
  leftCaption,
  pnl,
}: {
  label: string;
  note?: string;
  /** Bar height as a 0-100 percentage; `muted` dims the column. */
  bars: {height: number; muted?: boolean}[];
  leftCaption: string;
  pnl: string;
}): ReactNode {
  return (
    <Shell label={label} note={note}>
      <div className={styles.bars}>
        {bars.map((b, i) => (
          <div
            key={i}
            className={`${styles.bar} ${b.muted ? styles.barMuted : ''}`}
            style={{height: `${b.height}%`}}
          />
        ))}
      </div>
      <div className={styles.barsCaption}>
        <span>{leftCaption}</span>
        <span className={styles.barsPnl}>{pnl}</span>
      </div>
    </Shell>
  );
}

/** One big number plus a small breakdown — liquidity-score, beginner pages. */
export function MetricVisual({
  label,
  note,
  value,
  unit,
  caption,
  rows,
}: {
  label: string;
  note?: string;
  value: string;
  unit?: string;
  caption: string;
  rows: {label: string; value: string}[];
}): ReactNode {
  return (
    <Shell label={label} note={note}>
      <div className={styles.metricValue}>
        {value}
        {unit ? <em> {unit}</em> : null}
      </div>
      <p className={styles.metricCaption}>{caption}</p>
      <div className={styles.metricRows}>
        {rows.map((r) => (
          <div key={r.label} className={styles.metricRow}>
            <span>{r.label}</span>
            <b>{r.value}</b>
          </div>
        ))}
      </div>
    </Shell>
  );
}

/** Recurring-buy timeline — DCA pages. */
export function ScheduleVisual({
  label,
  note,
  rows,
}: {
  label: string;
  note?: string;
  rows: {date: string; detail: string; amount: string}[];
}): ReactNode {
  return (
    <Shell label={label} note={note}>
      <div className={styles.schedule}>
        {rows.map((r) => (
          <div key={r.date} className={styles.scheduleRow}>
            <span className={styles.scheduleDot} aria-hidden="true" />
            <span className={styles.scheduleDate}>{r.date}</span>
            <span>{r.detail}</span>
            <span className={styles.scheduleAmount}>{r.amount}</span>
          </div>
        ))}
      </div>
    </Shell>
  );
}

/** Mono code snippet — API, embeddable widget, app-builder pages. */
export function CodeVisual({
  label,
  note,
  lines,
}: {
  label: string;
  note?: string;
  /** A plain string is code; `{comment}` renders dimmed. */
  lines: (string | {comment: string})[];
}): ReactNode {
  return (
    <Shell label={label} note={note}>
      <pre className={styles.code}>
        {lines.map((line, i) => (
          <span key={i}>
            {typeof line === 'string' ? (
              line
            ) : (
              <span className={styles.codeComment}>{line.comment}</span>
            )}
            {'\n'}
          </span>
        ))}
      </pre>
    </Shell>
  );
}

/** Framed app/widget mock — white-label, brokerage pages. */
export function DeviceVisual({
  label,
  note,
  lines,
  cta,
}: {
  label: string;
  note?: string;
  /** Each entry is a 0-100 width percentage; `accent` brightens the row. */
  lines: {width: number; accent?: boolean}[];
  cta: string;
}): ReactNode {
  return (
    <Shell label={label} note={note}>
      <div className={styles.device}>
        <div className={styles.deviceBar} aria-hidden="true">
          <span />
          <span />
          <span />
        </div>
        {lines.map((l, i) => (
          <div
            key={i}
            className={`${styles.deviceLine} ${
              l.accent ? styles.deviceLineAccent : ''
            }`}
            style={{width: `${l.width}%`}}
          />
        ))}
        <div className={styles.deviceCta}>{cta}</div>
      </div>
    </Shell>
  );
}
