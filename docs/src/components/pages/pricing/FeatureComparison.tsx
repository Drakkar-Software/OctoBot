import React, {type ReactNode} from 'react';
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

const COLUMNS = ['Feature', 'Investor', 'Investor Plus', 'Pro'];

const CATEGORIES: ComparisonCategory[] = [
  {
    name: 'Strategies',
    rows: [
      {feature: 'Simple strategies', values: ['Limited', 'Unlimited', 'Unlimited']},
      {feature: 'Advanced strategies', values: ['—', 'Unlimited', 'Unlimited']},
      {feature: 'Strategy designer', values: ['—', '✓', '✓']},
    ],
  },
  {
    name: 'Bots',
    rows: [
      {
        feature: 'Maximum simultaneous OctoBots',
        values: ['1 bot', '10 bots', '20 bots'],
      },
      {feature: 'DCA / Grid / AI bots', values: ['✓', '✓', '✓']},
      {feature: 'Copy trading bot', values: ['—', '✓', '✓']},
    ],
  },
  {
    name: 'Trading',
    rows: [
      {feature: 'Paper trading', values: ['✓', '✓', '✓']},
      {
        feature: 'Paper trading duration',
        values: ['14 days', '30 days', 'Unlimited'],
      },
      {feature: 'Futures trading', values: ['—', '—', '✓']},
    ],
  },
  {
    name: 'Portfolio management',
    rows: [
      {feature: 'Portfolio overview', values: ['✓', '✓', '✓']},
      {feature: 'Orders fine-tuning', values: ['—', '✓', '✓']},
      {feature: 'Balance limit', values: ['$1000', 'Unlimited', 'Unlimited']},
    ],
  },
  {
    name: 'AI features',
    rows: [
      {feature: 'ChatGPT integration', values: ['—', '✓', '✓']},
      {feature: 'Customize strategy with AI', values: ['—', '✓', '✓']},
      {
        feature: 'Personalized arbitrage & AI signals',
        values: ['—', '—', '✓'],
      },
    ],
  },
  {
    name: 'Extra Features',
    rows: [
      {feature: 'Mobile app', values: ['✓', '✓', '✓']},
      {feature: 'Priority support', values: ['—', '—', '✓']},
      {feature: 'Summarized crypto news', values: ['—', '✓', '✓']},
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
