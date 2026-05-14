import React, {useEffect, useRef, type ReactNode} from 'react';
import BrowserOnly from '@docusaurus/BrowserOnly';
import styles from './styles.module.css';

interface TradingViewWidgetProps {
  /** Full TradingView symbol, e.g. "BINANCE:BTCUSDT". */
  symbol: string;
  /** Chart height in px. Default 420. */
  height?: number;
}

/**
 * Client-only TradingView advanced-chart embed. TradingView's embed script is
 * free and key-less; it renders by reading a JSON config from a script tag
 * appended into its container, so it has to run in the browser — wrapped in
 * <BrowserOnly> to stay SSR-safe.
 */
function Widget({symbol, height = 420}: TradingViewWidgetProps): ReactNode {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) {
      return;
    }
    const script = document.createElement('script');
    script.src =
      'https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js';
    script.async = true;
    script.innerHTML = JSON.stringify({
      symbol,
      theme: 'dark',
      style: '1',
      locale: 'en',
      width: '100%',
      height,
      hide_side_toolbar: true,
      allow_symbol_change: false,
      backgroundColor: 'rgba(0, 0, 0, 0)',
    });
    container.appendChild(script);
    return () => {
      container.innerHTML = '';
    };
  }, [symbol, height]);

  return (
    <div
      className={styles.container}
      ref={containerRef}
      style={{height}}
      aria-label={`${symbol} price chart`}
    />
  );
}

export default function TradingViewWidget(
  props: TradingViewWidgetProps,
): ReactNode {
  return (
    <BrowserOnly
      fallback={<div className={styles.container} style={{height: props.height ?? 420}} />}>
      {() => <Widget {...props} />}
    </BrowserOnly>
  );
}
