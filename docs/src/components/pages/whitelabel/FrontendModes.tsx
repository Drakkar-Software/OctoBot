import React, {useState, type ReactNode} from 'react';
import {translate} from '@docusaurus/Translate';
import GlassCard from '@site/src/components/GlassCard';
import styles from './FrontendModes.module.css';

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

const SHIP = translate({
  id: 'pages.whitelabel.frontendModes.fact.ship',
  message: 'Ship',
  description: 'Frontend modes fact label',
});
const BRAND = translate({
  id: 'pages.whitelabel.frontendModes.fact.brand',
  message: 'Brand',
  description: 'Frontend modes fact label',
});
const AUTH = translate({
  id: 'pages.whitelabel.frontendModes.fact.auth',
  message: 'Auth',
  description: 'Frontend modes fact label',
});
const BEST_FOR = translate({
  id: 'pages.whitelabel.frontendModes.fact.bestFor',
  message: 'Best for',
  description: 'Frontend modes fact label',
});

const MODES: Mode[] = [
  {
    id: 'widget',
    label: translate({
      id: 'pages.whitelabel.frontendModes.widget.label',
      message: 'Embedded widget',
      description: 'Frontend modes tab label',
    }),
    title: translate({
      id: 'pages.whitelabel.frontendModes.widget.title',
      message: 'Embedded widget',
      description: 'Frontend modes panel title',
    }),
    sub: translate({
      id: 'pages.whitelabel.frontendModes.widget.sub',
      message:
        'A React/Vue component that drops into your existing client. The trading tab, without the rebuild.',
      description: 'Frontend modes panel sub',
    }),
    facts: [
      {
        label: SHIP,
        value: translate({
          id: 'pages.whitelabel.frontendModes.widget.ship',
          message: 'React/Vue component',
          description: 'Frontend modes fact value',
        }),
      },
      {
        label: BRAND,
        value: translate({
          id: 'pages.whitelabel.frontendModes.widget.brand',
          message: 'Design tokens + logo',
          description: 'Frontend modes fact value',
        }),
      },
      {
        label: AUTH,
        value: translate({
          id: 'pages.whitelabel.frontendModes.widget.auth',
          message: 'Hooks into yours',
          description: 'Frontend modes fact value',
        }),
      },
      {
        label: BEST_FOR,
        value: translate({
          id: 'pages.whitelabel.frontendModes.widget.bestFor',
          message: 'adding a trading tab',
          description: 'Frontend modes fact value',
        }),
        tag: true,
      },
    ],
  },
  {
    id: 'web',
    label: translate({
      id: 'pages.whitelabel.frontendModes.web.label',
      message: 'Full web app',
      description: 'Frontend modes tab label',
    }),
    title: translate({
      id: 'pages.whitelabel.frontendModes.web.title',
      message: 'Full web app',
      description: 'Frontend modes panel title',
    }),
    sub: translate({
      id: 'pages.whitelabel.frontendModes.web.sub',
      message:
        'A forkable Next.js app on a standalone domain. Layout, copy, screens — all editable.',
      description: 'Frontend modes panel sub',
    }),
    facts: [
      {
        label: SHIP,
        value: translate({
          id: 'pages.whitelabel.frontendModes.web.ship',
          message: 'Forkable Next.js app',
          description: 'Frontend modes fact value',
        }),
      },
      {
        label: BRAND,
        value: translate({
          id: 'pages.whitelabel.frontendModes.web.brand',
          message: 'Tokens, layout, copy, screens',
          description: 'Frontend modes fact value',
        }),
      },
      {
        label: AUTH,
        value: translate({
          id: 'pages.whitelabel.frontendModes.web.auth',
          message: 'OIDC · SAML · custom',
          description: 'Frontend modes fact value',
        }),
      },
      {
        label: BEST_FOR,
        value: translate({
          id: 'pages.whitelabel.frontendModes.web.bestFor',
          message: 'launching a wealth product',
          description: 'Frontend modes fact value',
        }),
        tag: true,
      },
    ],
  },
  {
    id: 'mobile',
    label: translate({
      id: 'pages.whitelabel.frontendModes.mobile.label',
      message: 'Native mobile',
      description: 'Frontend modes tab label',
    }),
    title: translate({
      id: 'pages.whitelabel.frontendModes.mobile.title',
      message: 'Native mobile',
      description: 'Frontend modes panel title',
    }),
    sub: translate({
      id: 'pages.whitelabel.frontendModes.mobile.sub',
      message:
        'iOS + Android source. Ships under your name in the App Store and Play Store.',
      description: 'Frontend modes panel sub',
    }),
    facts: [
      {
        label: SHIP,
        value: translate({
          id: 'pages.whitelabel.frontendModes.mobile.ship',
          message: 'iOS + Android source',
          description: 'Frontend modes fact value',
        }),
      },
      {
        label: BRAND,
        value: translate({
          id: 'pages.whitelabel.frontendModes.mobile.brand',
          message: 'Icons, splash, store listing',
          description: 'Frontend modes fact value',
        }),
      },
      {
        label: AUTH,
        value: translate({
          id: 'pages.whitelabel.frontendModes.mobile.auth',
          message: 'OIDC · SAML · biometrics',
          description: 'Frontend modes fact value',
        }),
      },
      {
        label: BEST_FOR,
        value: translate({
          id: 'pages.whitelabel.frontendModes.mobile.bestFor',
          message: 'mobile-first brokers & neobanks',
          description: 'Frontend modes fact value',
        }),
        tag: true,
      },
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
