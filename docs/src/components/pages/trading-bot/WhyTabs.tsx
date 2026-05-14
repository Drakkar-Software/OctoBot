import React, {useState, type ReactNode} from 'react';
import {translate} from '@docusaurus/Translate';
import GlassCard from '@site/src/components/GlassCard';
import styles from './WhyTabs.module.css';

/*
 * Page-local tab switcher for the /trading-bot page — "Why using OctoBot?"
 * Four tabs, each rendering a glass card with a heading and a bullet list.
 * Bespoke useState picker, kept colocated with the trading-bot page.
 */

interface WhyTab {
  id: string;
  label: string;
  heading: string;
  bullets: string[];
}

const TABS: WhyTab[] = [
  {
    id: 'invest',
    label: translate({
      id: 'pages.tradingBot.whyTabs.invest.label',
      message: 'Invest',
      description: 'Why tabs tab label',
    }),
    heading: translate({
      id: 'pages.tradingBot.whyTabs.invest.heading',
      message: 'Invest in your crypto with your strategies',
      description: 'Why tabs panel heading',
    }),
    bullets: [
      translate({
        id: 'pages.tradingBot.whyTabs.invest.bullet1',
        message: 'Technical analysis & AI',
        description: 'Why tabs panel bullet',
      }),
      translate({
        id: 'pages.tradingBot.whyTabs.invest.bullet2',
        message: 'Smart Dollar Cost Averaging & Grid trading',
        description: 'Why tabs panel bullet',
      }),
      translate({
        id: 'pages.tradingBot.whyTabs.invest.bullet3',
        message: 'TradingView automation',
        description: 'Why tabs panel bullet',
      }),
    ],
  },
  {
    id: 'create',
    label: translate({
      id: 'pages.tradingBot.whyTabs.create.label',
      message: 'Create',
      description: 'Why tabs tab label',
    }),
    heading: translate({
      id: 'pages.tradingBot.whyTabs.create.heading',
      message: 'Create, optimize and trade with your own strategies',
      description: 'Why tabs panel heading',
    }),
    bullets: [
      translate({
        id: 'pages.tradingBot.whyTabs.create.bullet1',
        message: 'Trade SPOT and Futures markets',
        description: 'Why tabs panel bullet',
      }),
      translate({
        id: 'pages.tradingBot.whyTabs.create.bullet2',
        message: 'Use your unique strategy',
        description: 'Why tabs panel bullet',
      }),
      translate({
        id: 'pages.tradingBot.whyTabs.create.bullet3',
        message: 'Optimize it with backtesting',
        description: 'Why tabs panel bullet',
      }),
    ],
  },
  {
    id: 'autopilot',
    label: translate({
      id: 'pages.tradingBot.whyTabs.autopilot.label',
      message: 'Autopilot',
      description: 'Why tabs tab label',
    }),
    heading: translate({
      id: 'pages.tradingBot.whyTabs.autopilot.heading',
      message: 'Profit from well-known strategies',
      description: 'Why tabs panel heading',
    }),
    bullets: [
      translate({
        id: 'pages.tradingBot.whyTabs.autopilot.bullet1',
        message:
          'Run ready-to-use trading strategies to diversify your investments',
        description: 'Why tabs panel bullet',
      }),
      translate({
        id: 'pages.tradingBot.whyTabs.autopilot.bullet2',
        message: 'Totally free: enjoy all trading strategies at no cost',
        description: 'Why tabs panel bullet',
      }),
    ],
  },
  {
    id: 'follow',
    label: translate({
      id: 'pages.tradingBot.whyTabs.follow.label',
      message: 'Follow',
      description: 'Why tabs tab label',
    }),
    heading: translate({
      id: 'pages.tradingBot.whyTabs.follow.heading',
      message: 'Follow your OctoBots from anywhere',
      description: 'Why tabs panel heading',
    }),
    bullets: [
      translate({
        id: 'pages.tradingBot.whyTabs.follow.bullet1',
        message: 'From any web browser, on mobile or desktop',
        description: 'Why tabs panel bullet',
      }),
      translate({
        id: 'pages.tradingBot.whyTabs.follow.bullet2',
        message: 'From your phone with the OctoBot App or Telegram',
        description: 'Why tabs panel bullet',
      }),
    ],
  },
];

export default function WhyTabs(): ReactNode {
  const [active, setActive] = useState(0);
  const tab = TABS[active];

  return (
    <div className={styles.wrap}>
      <div
        className={styles.tabs}
        role="tablist"
        aria-label={translate({
          id: 'pages.tradingBot.whyTabs.ariaLabel',
          message: 'Why using OctoBot',
          description: 'Why tabs tablist accessibility label',
        })}>
        {TABS.map((t, i) => (
          <button
            key={t.id}
            type="button"
            role="tab"
            aria-selected={i === active}
            className={i === active ? styles.tabOn : styles.tab}
            onClick={() => setActive(i)}>
            {t.label}
          </button>
        ))}
      </div>

      <GlassCard variant="strong" className={styles.panel}>
        <h3 className={styles.heading}>{tab.heading}</h3>
        <ul className={styles.bullets}>
          {tab.bullets.map((bullet) => (
            <li key={bullet} className={styles.bullet}>
              <span className={styles.dot} aria-hidden="true" />
              <span>{bullet}</span>
            </li>
          ))}
        </ul>
      </GlassCard>
    </div>
  );
}
