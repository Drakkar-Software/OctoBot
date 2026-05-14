import React, {useState, type ReactNode} from 'react';
import GlassCard from '@site/src/components/GlassCard';
import styles from './SkinSwitcher.module.css';

/*
 * Page-local hero visual — a tab picker that re-skins a mini trading UI to
 * show off the white-label nature of the product. Bespoke theme state, kept
 * with the /whitelabel page.
 */

interface Theme {
  id: string;
  name: string;
  mark: string;
  vars: React.CSSProperties;
}

const THEMES: Theme[] = [
  {
    id: 'octo',
    name: 'OctoBot',
    mark: '◐',
    vars: {
      '--bk-bg': '#0a0d2c',
      '--bk-ink': '#f3f6f8',
      '--bk-muted': 'rgba(243,246,248,0.6)',
      '--bk-card': 'rgba(255,255,255,0.06)',
      '--bk-rule': 'rgba(255,255,255,0.1)',
      '--bk-accent': '#65e7cf',
      '--bk-glow': 'rgba(101,231,207,0.22)',
    } as React.CSSProperties,
  },
  {
    id: 'ember',
    name: 'Ember Trade',
    mark: '✦',
    vars: {
      '--bk-bg': '#14100b',
      '--bk-ink': '#faf6f0',
      '--bk-muted': 'rgba(250,246,240,0.6)',
      '--bk-card': 'rgba(255,255,255,0.04)',
      '--bk-rule': 'rgba(255,255,255,0.08)',
      '--bk-accent': '#f59e3a',
      '--bk-glow': 'rgba(245,158,58,0.22)',
    } as React.CSSProperties,
  },
  {
    id: 'noir',
    name: 'Noir Capital',
    mark: '■',
    vars: {
      '--bk-bg': '#0a0a0a',
      '--bk-ink': '#f7f7f7',
      '--bk-muted': 'rgba(247,247,247,0.55)',
      '--bk-card': 'rgba(255,255,255,0.04)',
      '--bk-rule': 'rgba(255,255,255,0.08)',
      '--bk-accent': '#ffffff',
      '--bk-glow': 'rgba(255,255,255,0.16)',
    } as React.CSSProperties,
  },
  {
    id: 'violet',
    name: 'Lyra Wealth',
    mark: '◆',
    vars: {
      '--bk-bg': '#100a1e',
      '--bk-ink': '#f4ecff',
      '--bk-muted': 'rgba(244,236,255,0.6)',
      '--bk-card': 'rgba(255,255,255,0.05)',
      '--bk-rule': 'rgba(255,255,255,0.08)',
      '--bk-accent': '#b890ff',
      '--bk-glow': 'rgba(184,144,255,0.24)',
    } as React.CSSProperties,
  },
];

export default function SkinSwitcher(): ReactNode {
  const [active, setActive] = useState(0);
  const theme = THEMES[active];

  return (
    <GlassCard variant="strong" padded={false} className={styles.card}>
      <div className={styles.tabs}>
        {THEMES.map((t, i) => (
          <button
            key={t.id}
            type="button"
            className={i === active ? styles.tabOn : styles.tab}
            onClick={() => setActive(i)}>
            {t.name}
          </button>
        ))}
      </div>

      <div className={styles.stage} style={theme.vars}>
        <div className={styles.bkHead}>
          <div className={styles.bkLogo}>
            <span className={styles.bkMark}>{theme.mark}</span>
            <span>{theme.name}</span>
          </div>
          <span className={styles.bkPill}>Powered by Octo</span>
        </div>

        <div className={styles.bkCard}>
          <div className={styles.bkLabel}>Portfolio · DCA Strategy</div>
          <div className={styles.bkValue}>€48,210.42</div>
          <div className={styles.bkRow}>
            <span className={styles.bkChip}>+14.6%</span>
            <span>since launch · 8 months</span>
          </div>
        </div>

        <div className={styles.bkStrats}>
          <div className={styles.bkStrat}>
            <div className={styles.bkStratName}>BTC · DCA Weekly</div>
            <div className={styles.bkStratPnl}>+12.4%</div>
          </div>
          <div className={styles.bkStrat}>
            <div className={styles.bkStratName}>ETH · Grid Bot</div>
            <div className={styles.bkStratPnl}>+8.2%</div>
          </div>
        </div>

        <div className={styles.bkBtn}>Start a new strategy</div>
      </div>
    </GlassCard>
  );
}
