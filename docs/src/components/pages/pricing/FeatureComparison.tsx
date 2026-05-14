import React, {type ReactNode} from 'react';
import {translate} from '@docusaurus/Translate';
import styles from './FeatureComparison.module.css';

/*
 * Page-local plan comparison table for the /pricing page.
 * A styled, horizontally scrollable table: a sticky-feel header row, then
 * feature rows grouped under category subheader rows. "✓" / "—" cells are
 * tone-colored; values use the mono font.
 */

type CellValue = string;

interface ComparisonRow {
  feature: string;
  values: [CellValue, CellValue, CellValue];
}

interface ComparisonCategory {
  name: string;
  rows: ComparisonRow[];
}

const LIMITED = translate({
  id: 'pages.pricing.comparison.value.limited',
  message: 'Limited',
  description: 'Feature comparison cell value',
});
const UNLIMITED = translate({
  id: 'pages.pricing.comparison.value.unlimited',
  message: 'Unlimited',
  description: 'Feature comparison cell value',
});

const COLUMNS = [
  translate({
    id: 'pages.pricing.comparison.column.feature',
    message: 'Feature',
    description: 'Feature comparison column header',
  }),
  translate({
    id: 'pages.pricing.comparison.column.investor',
    message: 'Investor',
    description: 'Feature comparison column header',
  }),
  translate({
    id: 'pages.pricing.comparison.column.investorPlus',
    message: 'Investor Plus',
    description: 'Feature comparison column header',
  }),
  translate({
    id: 'pages.pricing.comparison.column.pro',
    message: 'Pro',
    description: 'Feature comparison column header',
  }),
];

const CATEGORIES: ComparisonCategory[] = [
  {
    name: translate({
      id: 'pages.pricing.comparison.category.strategies',
      message: 'Strategies',
      description: 'Feature comparison category name',
    }),
    rows: [
      {
        feature: translate({
          id: 'pages.pricing.comparison.feature.simpleStrategies',
          message: 'Simple strategies',
          description: 'Feature comparison feature name',
        }),
        values: [LIMITED, UNLIMITED, UNLIMITED],
      },
      {
        feature: translate({
          id: 'pages.pricing.comparison.feature.advancedStrategies',
          message: 'Advanced strategies',
          description: 'Feature comparison feature name',
        }),
        values: ['—', UNLIMITED, UNLIMITED],
      },
      {
        feature: translate({
          id: 'pages.pricing.comparison.feature.strategyDesigner',
          message: 'Strategy designer',
          description: 'Feature comparison feature name',
        }),
        values: ['—', '✓', '✓'],
      },
    ],
  },
  {
    name: translate({
      id: 'pages.pricing.comparison.category.bots',
      message: 'Bots',
      description: 'Feature comparison category name',
    }),
    rows: [
      {
        feature: translate({
          id: 'pages.pricing.comparison.feature.maxBots',
          message: 'Maximum simultaneous OctoBots',
          description: 'Feature comparison feature name',
        }),
        values: [
          translate({
            id: 'pages.pricing.comparison.value.1bot',
            message: '1 bot',
            description: 'Feature comparison cell value',
          }),
          translate({
            id: 'pages.pricing.comparison.value.10bots',
            message: '10 bots',
            description: 'Feature comparison cell value',
          }),
          translate({
            id: 'pages.pricing.comparison.value.20bots',
            message: '20 bots',
            description: 'Feature comparison cell value',
          }),
        ],
      },
      {
        feature: translate({
          id: 'pages.pricing.comparison.feature.dcaGridAi',
          message: 'DCA / Grid / AI bots',
          description: 'Feature comparison feature name',
        }),
        values: ['✓', '✓', '✓'],
      },
      {
        feature: translate({
          id: 'pages.pricing.comparison.feature.copyTrading',
          message: 'Copy trading bot',
          description: 'Feature comparison feature name',
        }),
        values: ['—', '✓', '✓'],
      },
    ],
  },
  {
    name: translate({
      id: 'pages.pricing.comparison.category.trading',
      message: 'Trading',
      description: 'Feature comparison category name',
    }),
    rows: [
      {
        feature: translate({
          id: 'pages.pricing.comparison.feature.paperTrading',
          message: 'Paper trading',
          description: 'Feature comparison feature name',
        }),
        values: ['✓', '✓', '✓'],
      },
      {
        feature: translate({
          id: 'pages.pricing.comparison.feature.paperTradingDuration',
          message: 'Paper trading duration',
          description: 'Feature comparison feature name',
        }),
        values: [
          translate({
            id: 'pages.pricing.comparison.value.14days',
            message: '14 days',
            description: 'Feature comparison cell value',
          }),
          translate({
            id: 'pages.pricing.comparison.value.30days',
            message: '30 days',
            description: 'Feature comparison cell value',
          }),
          UNLIMITED,
        ],
      },
      {
        feature: translate({
          id: 'pages.pricing.comparison.feature.futuresTrading',
          message: 'Futures trading',
          description: 'Feature comparison feature name',
        }),
        values: ['—', '—', '✓'],
      },
    ],
  },
  {
    name: translate({
      id: 'pages.pricing.comparison.category.portfolio',
      message: 'Portfolio management',
      description: 'Feature comparison category name',
    }),
    rows: [
      {
        feature: translate({
          id: 'pages.pricing.comparison.feature.portfolioOverview',
          message: 'Portfolio overview',
          description: 'Feature comparison feature name',
        }),
        values: ['✓', '✓', '✓'],
      },
      {
        feature: translate({
          id: 'pages.pricing.comparison.feature.ordersFineTuning',
          message: 'Orders fine-tuning',
          description: 'Feature comparison feature name',
        }),
        values: ['—', '✓', '✓'],
      },
      {
        feature: translate({
          id: 'pages.pricing.comparison.feature.balanceLimit',
          message: 'Balance limit',
          description: 'Feature comparison feature name',
        }),
        values: [
          translate({
            id: 'pages.pricing.comparison.value.1000',
            message: '$1000',
            description: 'Feature comparison cell value',
          }),
          UNLIMITED,
          UNLIMITED,
        ],
      },
    ],
  },
  {
    name: translate({
      id: 'pages.pricing.comparison.category.ai',
      message: 'AI features',
      description: 'Feature comparison category name',
    }),
    rows: [
      {
        feature: translate({
          id: 'pages.pricing.comparison.feature.chatgpt',
          message: 'ChatGPT integration',
          description: 'Feature comparison feature name',
        }),
        values: ['—', '✓', '✓'],
      },
      {
        feature: translate({
          id: 'pages.pricing.comparison.feature.customizeAi',
          message: 'Customize strategy with AI',
          description: 'Feature comparison feature name',
        }),
        values: ['—', '✓', '✓'],
      },
      {
        feature: translate({
          id: 'pages.pricing.comparison.feature.arbitrage',
          message: 'Personalized arbitrage & AI signals',
          description: 'Feature comparison feature name',
        }),
        values: ['—', '—', '✓'],
      },
    ],
  },
  {
    name: translate({
      id: 'pages.pricing.comparison.category.extra',
      message: 'Extra Features',
      description: 'Feature comparison category name',
    }),
    rows: [
      {
        feature: translate({
          id: 'pages.pricing.comparison.feature.mobileApp',
          message: 'Mobile app',
          description: 'Feature comparison feature name',
        }),
        values: ['✓', '✓', '✓'],
      },
      {
        feature: translate({
          id: 'pages.pricing.comparison.feature.prioritySupport',
          message: 'Priority support',
          description: 'Feature comparison feature name',
        }),
        values: ['—', '—', '✓'],
      },
      {
        feature: translate({
          id: 'pages.pricing.comparison.feature.cryptoNews',
          message: 'Summarized crypto news',
          description: 'Feature comparison feature name',
        }),
        values: ['—', '✓', '✓'],
      },
    ],
  },
];

function ValueCell({value}: {value: CellValue}): ReactNode {
  if (value === '✓') {
    return <span className={styles.yes}>✓</span>;
  }
  if (value === '—') {
    return <span className={styles.no}>—</span>;
  }
  return <span className={styles.text}>{value}</span>;
}

export default function FeatureComparison(): ReactNode {
  return (
    <div className={styles.scroll}>
      <table className={styles.table}>
        <thead>
          <tr className={styles.headRow}>
            {COLUMNS.map((col, i) => (
              <th
                key={col}
                className={i === 0 ? styles.headFeature : styles.headPlan}>
                {col}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {CATEGORIES.map((category) => (
            <React.Fragment key={category.name}>
              <tr className={styles.categoryRow}>
                <th colSpan={COLUMNS.length} className={styles.categoryCell}>
                  {category.name}
                </th>
              </tr>
              {category.rows.map((row) => (
                <tr key={row.feature} className={styles.row}>
                  <td className={styles.featureCell}>{row.feature}</td>
                  {row.values.map((value, i) => (
                    <td key={i} className={styles.valueCell}>
                      <ValueCell value={value} />
                    </td>
                  ))}
                </tr>
              ))}
            </React.Fragment>
          ))}
        </tbody>
      </table>
    </div>
  );
}
