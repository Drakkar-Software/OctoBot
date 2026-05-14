import React, {useState, type ReactNode} from 'react';
import Translate, {translate} from '@docusaurus/Translate';
import type {Cryptocurrency} from '../types';
import styles from './ConverterWidget.module.css';

interface ConverterWidgetProps {
  base: Cryptocurrency;
  quote: Cryptocurrency;
}

/**
 * Static-rate base -> quote calculator. Both sides carry a USD `lastPrice`
 * from the build-time endpoint payload (USD itself is priced at 1), so the
 * conversion rate is simply base.lastPrice / quote.lastPrice. No live data,
 * no network — the rate is fixed at build time and labelled as such.
 */
function format(value: number): string {
  if (!Number.isFinite(value)) {
    return '—';
  }
  const abs = Math.abs(value);
  const digits = abs >= 1 ? 2 : abs >= 0.01 ? 6 : 10;
  return value.toLocaleString('en-US', {maximumFractionDigits: digits});
}

export default function ConverterWidget({
  base,
  quote,
}: ConverterWidgetProps): ReactNode {
  const [amount, setAmount] = useState('1');

  const rate =
    quote.lastPrice > 0 ? base.lastPrice / quote.lastPrice : Number.NaN;
  const parsed = Number(amount.replace(',', '.'));
  const converted = Number.isFinite(parsed) ? parsed * rate : Number.NaN;

  return (
    <div className={`ng-card-strong ${styles.card}`}>
      <div className={styles.row}>
        <label className={styles.field}>
          <span className={styles.label}>{base.symbol.toUpperCase()}</span>
          <input
            className={styles.input}
            inputMode="decimal"
            value={amount}
            onChange={(event) => setAmount(event.target.value)}
            aria-label={translate(
              {
                id: 'programmatic.converterWidget.amountLabel',
                message: 'Amount in {symbol}',
                description:
                  'Accessible label for the converter amount input; {symbol} is the base ticker',
              },
              {symbol: base.symbol.toUpperCase()},
            )}
          />
        </label>
        <div className={styles.equals} aria-hidden="true">
          =
        </div>
        <div className={styles.field}>
          <span className={styles.label}>{quote.symbol.toUpperCase()}</span>
          <div className={`${styles.input} ${styles.output}`}>
            {format(converted)}
          </div>
        </div>
      </div>
      <p className={styles.rate}>
        <Translate
          id="programmatic.converterWidget.rate"
          description="Build-time conversion rate line; {base}/{quote} are tickers, {rate} the formatted rate value"
          values={{
            base: base.symbol.toUpperCase(),
            quote: quote.symbol.toUpperCase(),
            rate: format(rate),
          }}>
          {'1 {base} = {rate} {quote} · build-time rate'}
        </Translate>
      </p>
    </div>
  );
}
