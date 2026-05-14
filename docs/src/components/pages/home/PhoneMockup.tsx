import React, {useState, type ReactNode} from 'react';
import Translate, {translate} from '@docusaurus/Translate';
import styles from './PhoneMockup.module.css';

/*
 * Page-local hero visual — a phone frame with three switchable panels
 * (Track / Automate / Goals). One-off: holds tab state and bespoke layout,
 * so it is colocated with the /app page rather than promoted to a generic
 * landing component. The leading underscore keeps Docusaurus from turning
 * this file into a route.
 */

type Panel = 'track' | 'automate' | 'goals';

const TABS: {id: Panel; label: string}[] = [
  {
    id: 'track',
    label: translate({
      id: 'pages.index.phone.tab.track',
      message: 'Track',
      description: 'Phone mockup tab label',
    }),
  },
  {
    id: 'automate',
    label: translate({
      id: 'pages.index.phone.tab.automate',
      message: 'Automate',
      description: 'Phone mockup tab label',
    }),
  },
  {
    id: 'goals',
    label: translate({
      id: 'pages.index.phone.tab.goals',
      message: 'Goals',
      description: 'Phone mockup tab label',
    }),
  },
];

const STRATEGIES = [
  {
    code: 'DC',
    name: translate({
      id: 'pages.index.phone.strategies.dca.name',
      message: 'BTC weekly DCA',
      description: 'Phone mockup strategy name',
    }),
    venue: translate({
      id: 'pages.index.phone.strategies.dca.venue',
      message: 'Binance · spot',
      description: 'Phone mockup strategy venue',
    }),
    pct: '+18.4%',
  },
  {
    code: 'GR',
    name: translate({
      id: 'pages.index.phone.strategies.grid.name',
      message: 'ETH range grid',
      description: 'Phone mockup strategy name',
    }),
    venue: translate({
      id: 'pages.index.phone.strategies.grid.venue',
      message: 'Kraken · spot',
      description: 'Phone mockup strategy venue',
    }),
    pct: '+9.1%',
  },
  {
    code: 'SG',
    name: translate({
      id: 'pages.index.phone.strategies.signals.name',
      message: 'TV signals · perps',
      description: 'Phone mockup strategy name',
    }),
    venue: translate({
      id: 'pages.index.phone.strategies.signals.venue',
      message: 'Bybit · futures',
      description: 'Phone mockup strategy venue',
    }),
    pct: '+24.6%',
  },
];

const GOALS = [
  {
    name: translate({
      id: 'pages.index.phone.goals.house.name',
      message: 'House down payment',
      description: 'Phone mockup goal name',
    }),
    pct: 68,
    accent: false,
    detail: translate({
      id: 'pages.index.phone.goals.house.detail',
      message: '€68k of €100k',
      description: 'Phone mockup goal detail',
    }),
    eta: 'JUN 2027',
  },
  {
    name: translate({
      id: 'pages.index.phone.goals.retirement.name',
      message: 'Retirement runway',
      description: 'Phone mockup goal name',
    }),
    pct: 42,
    accent: true,
    detail: translate({
      id: 'pages.index.phone.goals.retirement.detail',
      message: '€210k of €500k',
      description: 'Phone mockup goal detail',
    }),
    eta: '2029',
  },
];

function TrackPanel(): ReactNode {
  return (
    <div className={styles.panel}>
      <div className={styles.devHead}>
        <div className={styles.pn}>
          <Translate
            id="pages.index.phone.track.balanceLabel"
            description="Phone mockup track panel label">
            Total balance
          </Translate>
        </div>
        <div className={styles.nw}>€184,920</div>
        <div className={styles.delta}>
          +€12,420 <span>· +7.2% · 30d</span>
        </div>
      </div>
      <div className={styles.chart}>
        <svg viewBox="0 0 280 110" preserveAspectRatio="none">
          <defs>
            <linearGradient id="ngPhoneChart" x1="0" x2="0" y1="0" y2="1">
              <stop offset="0%" stopColor="#65e7cf" stopOpacity="0.55" />
              <stop offset="100%" stopColor="#65e7cf" stopOpacity="0" />
            </linearGradient>
          </defs>
          <path
            d="M0,88 C20,82 35,90 55,74 C75,58 95,62 115,52 C135,42 155,46 175,34 C195,22 215,28 235,16 L280,8 L280,110 L0,110 Z"
            fill="url(#ngPhoneChart)"
          />
          <path
            d="M0,88 C20,82 35,90 55,74 C75,58 95,62 115,52 C135,42 155,46 175,34 C195,22 215,28 235,16 L280,8"
            stroke="#65e7cf"
            strokeWidth="1.8"
            fill="none"
          />
          <circle cx="280" cy="8" r="3" fill="#65e7cf" />
          <circle cx="280" cy="8" r="6" fill="#65e7cf" opacity="0.25" />
        </svg>
      </div>
      <div className={styles.running}>
        <span className={styles.runDot} />
        <div>
          <Translate
            id="pages.index.phone.track.running"
            description="Phone mockup track panel running strategies count">
            3 strategies running
          </Translate>
        </div>
        <span className={styles.runPct}>+12.4%</span>
      </div>
    </div>
  );
}

function AutomatePanel(): ReactNode {
  return (
    <div className={styles.panel}>
      <div className={styles.devHead}>
        <div className={styles.pn}>
          <Translate
            id="pages.index.phone.automate.label"
            description="Phone mockup automate panel label">
            Strategies
          </Translate>
        </div>
        <div className={styles.nwSm}>
          3 <span>+12.4%</span>
        </div>
        <div className={styles.deltaFaint}>
          <Translate
            id="pages.index.phone.automate.sub"
            description="Phone mockup automate panel sub">
            live · across 3 venues
          </Translate>
        </div>
      </div>
      <div className={styles.strats}>
        {STRATEGIES.map((s) => (
          <div key={s.code} className={styles.strat}>
            <span className={styles.stratIc}>{s.code}</span>
            <div className={styles.stratName}>
              {s.name}
              <s>{s.venue}</s>
            </div>
            <span className={styles.stratPct}>{s.pct}</span>
          </div>
        ))}
        <div className={styles.newStrat}>
          <Translate
            id="pages.index.phone.automate.newStrategy"
            description="Phone mockup new strategy button">
            + New strategy
          </Translate>
        </div>
      </div>
    </div>
  );
}

function GoalsPanel(): ReactNode {
  return (
    <div className={styles.panel}>
      <div className={styles.devHead}>
        <div className={styles.pn}>
          <Translate
            id="pages.index.phone.goals.label"
            description="Phone mockup goals panel label">
            Goals
          </Translate>
        </div>
        <div className={styles.nwSm}>
          2{' '}
          <span className={styles.frostSpan}>
            <Translate
              id="pages.index.phone.goals.onTrack"
              description="Phone mockup goals on-track status">
              on track
            </Translate>
          </span>
        </div>
        <div className={styles.deltaFaint}>
          <Translate
            id="pages.index.phone.goals.sub"
            description="Phone mockup goals panel sub">
            est. completion · 2027 – 2029
          </Translate>
        </div>
      </div>
      <div className={styles.goals}>
        {GOALS.map((g) => (
          <div key={g.name} className={styles.goal}>
            <div className={styles.goalHead}>
              <span className={styles.goalName}>{g.name}</span>
              <span
                className={styles.goalPc}
                style={g.accent ? {color: 'var(--ng-turquoise)'} : undefined}>
                {g.pct}%
              </span>
            </div>
            <div className={styles.bar}>
              <i
                className={g.accent ? styles.barFillAccent : styles.barFill}
                style={{width: `${g.pct}%`}}
              />
            </div>
            <div className={styles.goalSub}>
              <span>{g.detail}</span>
              <span>{g.eta}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

const PANELS: Record<Panel, () => ReactNode> = {
  track: TrackPanel,
  automate: AutomatePanel,
  goals: GoalsPanel,
};

export default function PhoneMockup(): ReactNode {
  const [active, setActive] = useState<Panel>('track');
  const ActivePanel = PANELS[active];

  return (
    <div className={styles.device}>
      <div className={styles.deviceGlow} />
      <div className={styles.screen}>
        <span
          className={styles.lock}
          title={translate({
            id: 'pages.index.phone.lockTitle',
            message: 'Keys encrypted on device',
            description: 'Phone mockup lock icon tooltip',
          })}
          aria-hidden="true">
          ⚿
        </span>

        <ActivePanel />

        <div className={styles.tabs} role="tablist">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              type="button"
              role="tab"
              aria-selected={active === tab.id}
              className={active === tab.id ? styles.tabOn : styles.tab}
              onClick={() => setActive(tab.id)}>
              {tab.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
