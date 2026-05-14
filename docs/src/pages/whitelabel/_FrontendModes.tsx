import React, {useState, type ReactNode} from 'react';
import GlassCard from '@site/src/components/GlassCard';
import styles from './_FrontendModes.module.css';

/*
 * Page-local frontend-mode picker — vertical tabs that swap a detail panel
 * (widget / web / mobile). Bespoke tab state, kept with the /whitelabel page.
 */

interface Mode {
  id: string;
  label: string;
  title: string;
  sub: string;
  facts: {label: string; value: string; tag?: boolean}[];
}

const MODES: Mode[] = [
  {
    id: 'widget',
    label: 'Embedded widget',
    title: 'Embedded widget',
    sub: 'A React/Vue component that drops into your existing client. The trading tab, without the rebuild.',
    facts: [
      {label: 'Ship', value: 'React/Vue component'},
      {label: 'Brand', value: 'Design tokens + logo'},
      {label: 'Auth', value: 'Hooks into yours'},
      {label: 'Best for', value: 'adding a trading tab', tag: true},
    ],
  },
  {
    id: 'web',
    label: 'Full web app',
    title: 'Full web app',
    sub: 'A forkable Next.js app on a standalone domain. Layout, copy, screens — all editable.',
    facts: [
      {label: 'Ship', value: 'Forkable Next.js app'},
      {label: 'Brand', value: 'Tokens, layout, copy, screens'},
      {label: 'Auth', value: 'OIDC · SAML · custom'},
      {label: 'Best for', value: 'launching a wealth product', tag: true},
    ],
  },
  {
    id: 'mobile',
    label: 'Native mobile',
    title: 'Native mobile',
    sub: 'iOS + Android source. Ships under your name in the App Store and Play Store.',
    facts: [
      {label: 'Ship', value: 'iOS + Android source'},
      {label: 'Brand', value: 'Icons, splash, store listing'},
      {label: 'Auth', value: 'OIDC · SAML · biometrics'},
      {label: 'Best for', value: 'mobile-first brokers & neobanks', tag: true},
    ],
  },
];

export default function FrontendModes(): ReactNode {
  const [active, setActive] = useState(0);
  const mode = MODES[active];

  return (
    <div className={styles.modes}>
      <div className={styles.tabs}>
        {MODES.map((m, i) => (
          <button
            key={m.id}
            type="button"
            className={i === active ? styles.tabOn : styles.tab}
            onClick={() => setActive(i)}>
            <span className={styles.tabNum}>
              {String(i + 1).padStart(2, '0')}
            </span>
            <span className={styles.tabLabel}>{m.label}</span>
          </button>
        ))}
      </div>

      <GlassCard variant="strong" padded={false} className={styles.panel}>
        <h3 className={styles.panelTitle}>{mode.title}</h3>
        <p className={styles.panelSub}>{mode.sub}</p>
        <div className={styles.facts}>
          {mode.facts.map((fact) => (
            <div key={fact.label} className={styles.fact}>
              <span className={styles.factLabel}>{fact.label}</span>
              <span
                className={fact.tag ? styles.factValueTag : styles.factValue}>
                {fact.value}
              </span>
            </div>
          ))}
        </div>
      </GlassCard>
    </div>
  );
}
