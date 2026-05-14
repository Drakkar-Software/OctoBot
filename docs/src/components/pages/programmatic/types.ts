/**
 * Shapes returned by the OctoBot Cloud programmatic-slugs endpoint and passed
 * into the programmatic page templates via the plugin's route `modules`.
 */

export interface FaqEntry {
  question: string;
  answer: string;
}

export interface Cryptocurrency {
  symbol: string;
  name: string;
  slug: string;
  /** Last known price in USD. USD itself is modelled with lastPrice 1. */
  lastPrice: number;
  /** Localized "what is" prose — present only for documented coins. */
  whatIs?: string;
  faq?: FaqEntry[];
  hasPrediction?: boolean;
}

export type ExchangeSupportLevel = 'supported' | 'partial' | 'unsupported';

export interface ExchangeSupports {
  spot?: ExchangeSupportLevel;
  open_source?: ExchangeSupportLevel;
  market_making?: ExchangeSupportLevel;
}

export interface Exchange {
  name: string;
  slug: string;
  internalName: string;
  tier1?: boolean;
  supports?: ExchangeSupports;
}
