import React, {type ReactNode} from 'react';
import Translate, {translate} from '@docusaurus/Translate';
import PhoneMockup from './PhoneMockup';
import styles from './HeroStage.module.css';

/*
 * Page-local hero stage — the phone mockup flanked by floating glass stat
 * cards over a radial halo. Bespoke composition, kept with the /app page.
 */

const RUNNING = [
  {
    code: 'DC',
    name: translate({
      id: 'pages.index.heroStage.running.dca.name',
      message: 'BTC weekly DCA',
      description: 'Hero stage running strategy name',
    }),
    venue: translate({
      id: 'pages.index.heroStage.running.dca.venue',
      message: 'Binance · spot',
      description: 'Hero stage running strategy venue',
    }),
    pct: '+18.4%',
  },
  {
    code: 'GR',
    name: translate({
      id: 'pages.index.heroStage.running.grid.name',
      message: 'ETH range grid',
      description: 'Hero stage running strategy name',
    }),
    venue: translate({
      id: 'pages.index.heroStage.running.grid.venue',
      message: 'Kraken · spot',
      description: 'Hero stage running strategy venue',
    }),
    pct: '+9.1%',
  },
  {
    code: 'SG',
    name: translate({
      id: 'pages.index.heroStage.running.signals.name',
      message: 'TV signals · perps',
      description: 'Hero stage running strategy name',
    }),
    venue: translate({
      id: 'pages.index.heroStage.running.signals.venue',
      message: 'Bybit · futures',
      description: 'Hero stage running strategy venue',
    }),
    pct: '+24.6%',
  },
];

export default function HeroStage(): ReactNode {
  return (
    <div className={styles.stage}>
      <div className={styles.halo} />
      <div className={styles.inner}>
        {/* left float cards */}
        <div className={styles.side}>
          <div className={`ng-card-strong ${styles.card}`}>
            <div className={styles.lab}>
              <Translate
                id="pages.index.heroStage.netWorth.label"
                description="Hero stage card label">
                Net worth · 30d
              </Translate>
            </div>
            <div className={styles.value}>€184,920</div>
            <div className={styles.valueSub}>+€12,420 · +7.2%</div>
          </div>
          <div className={`ng-card-strong ${styles.card}`}>
            <div className={styles.lab}>
              <Translate
                id="pages.index.heroStage.diversification.label"
                description="Hero stage card label">
                Diversification
              </Translate>
            </div>
            <div className={styles.allocBar}>
              <span style={{flex: 4, background: '#f7931a'}} />
              <span style={{flex: 3, background: '#8aa1f0'}} />
              <span style={{flex: 2, background: 'var(--ng-warn)'}} />
              <span style={{flex: 1, background: 'var(--ng-pos)'}} />
            </div>
            <div className={styles.allocLegend}>
              <span>
                <span style={{color: '#f7931a'}}>●</span> BTC 40%
              </span>
              <span>
                <span style={{color: '#8aa1f0'}}>●</span> ETH 30%
              </span>
              <span>
                <span style={{color: 'var(--ng-warn)'}}>●</span> Gold 20%
              </span>
              <span>
                <span style={{color: 'var(--ng-pos)'}}>●</span> Cash 10%
              </span>
            </div>
          </div>
        </div>

        {/* device */}
        <PhoneMockup />

        {/* right float cards */}
        <div className={`${styles.side} ${styles.sideRight}`}>
          <div className={`ng-card-strong ${styles.card} ${styles.cardWide}`}>
            <div className={styles.lab}>
              <Translate
                id="pages.index.heroStage.running.label"
                description="Hero stage card label">
                Running on device
              </Translate>
            </div>
            {RUNNING.map((s) => (
              <div key={s.code} className={styles.stratRow}>
                <div className={styles.stratIc}>{s.code}</div>
                <div className={styles.stratName}>
                  {s.name}
                  <span>{s.venue}</span>
                </div>
                <div className={styles.stratPct}>{s.pct}</div>
              </div>
            ))}
          </div>
          <div className={`ng-card-strong ${styles.card}`}>
            <div className={styles.lab}>
              <Translate
                id="pages.index.heroStage.goal.label"
                description="Hero stage card label">
                Goal · House down payment
              </Translate>
            </div>
            <div className={styles.goalFigures}>
              <span className={styles.goalPct}>68%</span>
              <span className={styles.goalOf}>
                <Translate
                  id="pages.index.heroStage.goal.of"
                  description="Hero stage goal progress amount">
                  €68k of €100k
                </Translate>
              </span>
            </div>
            <div className={styles.goalBar}>
              <div className={styles.goalBarFill} style={{width: '68%'}} />
            </div>
            <div className={styles.valueSubNeutral}>
              <Translate
                id="pages.index.heroStage.goal.status"
                description="Hero stage goal status">
                On track · est. June 2027
              </Translate>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
