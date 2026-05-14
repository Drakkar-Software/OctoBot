import React, {type ReactNode} from 'react';
import PhoneMockup from './_PhoneMockup';
import styles from './_HeroStage.module.css';

/*
 * Page-local hero stage — the phone mockup flanked by floating glass stat
 * cards over a radial halo. Bespoke composition, kept with the /app page.
 */

const RUNNING = [
  {code: 'DC', name: 'BTC weekly DCA', venue: 'Binance · spot', pct: '+18.4%'},
  {code: 'GR', name: 'ETH range grid', venue: 'Kraken · spot', pct: '+9.1%'},
  {code: 'SG', name: 'TV signals · perps', venue: 'Bybit · futures', pct: '+24.6%'},
];

export default function HeroStage(): ReactNode {
  return (
    <div className={styles.stage}>
      <div className={styles.halo} />
      <div className={styles.inner}>
        {/* left float cards */}
        <div className={styles.side}>
          <div className={`ng-card-strong ${styles.card}`}>
            <div className={styles.lab}>Net worth · 30d</div>
            <div className={styles.value}>€184,920</div>
            <div className={styles.valueSub}>+€12,420 · +7.2%</div>
          </div>
          <div className={`ng-card-strong ${styles.card}`}>
            <div className={styles.lab}>Diversification</div>
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
            <div className={styles.lab}>Running on device</div>
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
            <div className={styles.lab}>Goal · House down payment</div>
            <div className={styles.goalFigures}>
              <span className={styles.goalPct}>68%</span>
              <span className={styles.goalOf}>€68k of €100k</span>
            </div>
            <div className={styles.goalBar}>
              <div className={styles.goalBarFill} style={{width: '68%'}} />
            </div>
            <div className={styles.valueSubNeutral}>On track · est. June 2027</div>
          </div>
        </div>
      </div>
    </div>
  );
}
