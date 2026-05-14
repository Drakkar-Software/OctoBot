/**
 * octobot-programmatic-pages — generates the SEO landing pages that don't map
 * to a single source file: per-coin explainers/predictions, per-exchange
 * trading-bot / market-maker pages, and the full crypto converter matrix.
 *
 * Docusaurus has no file-based dynamic route params, so these are added
 * programmatically at build time (loadContent -> contentLoaded -> addRoute),
 * the standard "many pages from data" plugin pattern.
 *
 * Data source: a single OctoBot Cloud endpoint, fetched live at build time,
 * once per locale. There is no committed fallback — if the endpoint is
 * unreachable the build fails by design.
 */

const DEFAULT_ENDPOINT = 'https://www.octobot.cloud/api/programmatic-slugs';

const ENDPOINT = process.env.OCTOBOT_PROGRAMMATIC_ENDPOINT || DEFAULT_ENDPOINT;

// USD is always available as a converter quote — modelled as a unit-priced
// "cryptocurrency" so the converter math (base.lastPrice / quote.lastPrice)
// stays uniform.
const USD = {symbol: 'USD', name: 'US Dollar', slug: 'usd', lastPrice: 1};

const TEMPLATE = (name) =>
  `@site/src/components/pages/programmatic/${name}/index.tsx`;

module.exports = function programmaticPagesPlugin(context) {
  const locale = context.i18n.currentLocale;

  return {
    name: 'octobot-programmatic-pages',

    async loadContent() {
      const url = `${ENDPOINT}?locale=${encodeURIComponent(locale)}`;
      let res;
      try {
        res = await fetch(url);
      } catch (err) {
        throw new Error(
          `[programmatic-pages] failed to reach ${url}: ${err.message}`,
        );
      }
      if (!res.ok) {
        throw new Error(
          `[programmatic-pages] ${url} returned ${res.status} ${res.statusText}`,
        );
      }
      const data = await res.json();
      if (
        !Array.isArray(data && data.cryptocurrencies) ||
        !Array.isArray(data && data.exchanges)
      ) {
        throw new Error(
          `[programmatic-pages] ${url} returned an unexpected shape — ` +
            'expected { cryptocurrencies: [], exchanges: [] }',
        );
      }
      return data;
    },

    async contentLoaded({content, actions}) {
      const {createData, addRoute} = actions;
      const {cryptocurrencies, exchanges} = content;

      // Shared once — referenced by every converter route instead of being
      // inlined into ~900 per-pair data files.
      const popularPath = await createData(
        'popular-cryptos.json',
        JSON.stringify(cryptocurrencies),
      );

      const emit = async (slug, key, template, data, extraModules) => {
        const dataPath = await createData(`${key}.json`, JSON.stringify(data));
        addRoute({
          path: `/${slug}`,
          component: template,
          modules: {data: dataPath, ...extraModules},
          exact: true,
        });
      };

      // Per-coin: what-is-<slug> and <symbol>-prediction.
      for (const crypto of cryptocurrencies) {
        const sym = crypto.symbol.toLowerCase();
        if (crypto.whatIs) {
          await emit(
            `what-is-${crypto.slug}`,
            `what-is-${crypto.slug}`,
            TEMPLATE('WhatIsCrypto'),
            {crypto},
          );
        }
        if (crypto.hasPrediction) {
          await emit(
            `${sym}-prediction`,
            `prediction-${sym}`,
            TEMPLATE('CryptoPrediction'),
            {crypto},
          );
        }
      }

      // Converter — full N×N matrix plus each coin against USD.
      const quotes = [...cryptocurrencies, USD];
      for (const base of cryptocurrencies) {
        const b = base.symbol.toLowerCase();
        for (const quote of quotes) {
          const q = quote.symbol.toLowerCase();
          if (b === q) continue;
          await emit(
            `tools/converter/${b}/${q}`,
            `converter-${b}-${q}`,
            TEMPLATE('ConverterPair'),
            {base, quote},
            {popular: popularPath},
          );
        }
      }

      // Per-exchange: trading-bot and market-maker.
      for (const exchange of exchanges) {
        const supports = exchange.supports || {};
        if (
          supports.spot === 'supported' ||
          supports.open_source === 'supported'
        ) {
          await emit(
            `${exchange.slug}-trading-bot`,
            `trading-bot-${exchange.slug}`,
            TEMPLATE('ExchangeTradingBot'),
            {exchange},
          );
        }
        if (supports.market_making === 'supported') {
          await emit(
            `${exchange.slug}-market-maker`,
            `market-maker-${exchange.slug}`,
            TEMPLATE('ExchangeMarketMaker'),
            {exchange},
          );
        }
      }
    },
  };
};
