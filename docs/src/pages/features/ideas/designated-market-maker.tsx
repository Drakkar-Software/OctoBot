import type {ReactNode} from 'react';
import Translate, {translate} from '@docusaurus/Translate';
import {IdeaPage, LadderVisual, type IdeaPageData} from '@site/src/components/pages/ideas';

/* SEO idea page — route: /features/ideas/designated-market-maker
 * Angle: the designated market maker role — committed spread and uptime obligations for a listing. */

const DATA: IdeaPageData = {
  meta: {
    title: translate({
      id: 'pages.ideas.designatedMm.meta.title',
      message: 'Designated Market Maker — committed liquidity for a token listing',
      description: 'Designated market maker page meta title',
    }),
    description: translate({
      id: 'pages.ideas.designatedMm.meta.description',
      message:
        'What a designated market maker does: a formal commitment to maximum spread, minimum depth and quoting uptime for a token or exchange listing. OctoBot Market Making quotes two-sided liquidity on centralized order-book venues.',
      description: 'Designated market maker page meta description',
    }),
  },
  hero: {
    eyebrow: translate({
      id: 'pages.ideas.designatedMm.hero.eyebrow',
      message: 'Role · Designated market maker',
      description: 'Designated market maker hero eyebrow',
    }),
    title: (
      <Translate
        id="pages.ideas.designatedMm.hero.title"
        description="Designated market maker hero title"
        values={{
          accent: (
            <span className="ng-text-gradient">
              {translate({
                id: 'pages.ideas.designatedMm.hero.title.accent',
                message: 'as a commitment.',
                description: 'Designated market maker hero title accent',
              })}
            </span>
          ),
        }}>
        {'Liquidity for your listing, {accent}'}
      </Translate>
    ),
    subtitle: translate({
      id: 'pages.ideas.designatedMm.hero.subtitle',
      message:
        'A designated market maker is the party that formally agrees to keep a token tradable — quoting both sides within an agreed spread, holding a minimum depth, and staying online for an agreed share of the time. It is market making with obligations attached.',
      description: 'Designated market maker hero subtitle',
    }),
    actions: [
      {
        label: translate({
          id: 'pages.ideas.designatedMm.hero.action.contact',
          message: 'Book a call',
          description: 'Designated market maker hero action label',
        }),
        to: 'mailto:contact@octobot.cloud',
      },
      {
        label: translate({
          id: 'pages.ideas.designatedMm.hero.action.feature',
          message: 'See OctoBot Market Making',
          description: 'Designated market maker hero action label',
        }),
        to: '/features/market-making',
        variant: 'ghost',
      },
    ],
    visual: (
      <LadderVisual
        label={translate({
          id: 'pages.ideas.designatedMm.visual.label',
          message: 'Committed two-sided quotes',
          description: 'Designated market maker visual label',
        })}
        note="spread within target"
        mid="$1.0000"
        asks={[
          {price: '$1.0030', size: '12,000', depth: 60},
          {price: '$1.0020', size: '9,000', depth: 45},
          {price: '$1.0010', size: '6,000', depth: 30},
        ]}
        bids={[
          {price: '$0.9990', size: '6,000', depth: 30},
          {price: '$0.9980', size: '9,000', depth: 45},
          {price: '$0.9970', size: '12,000', depth: 60},
        ]}
      />
    ),
  },
  sections: [
    {
      kind: 'callout',
      eyebrow: translate({
        id: 'pages.ideas.designatedMm.what.eyebrow',
        message: 'What it is',
        description: 'Designated market maker section eyebrow',
      }),
      title: translate({
        id: 'pages.ideas.designatedMm.what.title',
        message: 'A named party on the hook for keeping a market liquid',
        description: 'Designated market maker section title',
      }),
      body: translate({
        id: 'pages.ideas.designatedMm.what.body',
        message:
          'When a token gets listed, an exchange or the project itself often wants a guarantee that the order book will not be empty. A designated market maker fills that gap: it is a specific, named market maker that signs up to defined obligations — a maximum spread it will quote inside, a minimum size on each side, and a percentage of time it must be present. Exchanges want it because thin books scare away traders; projects want it because a tight, deep book makes the token look healthy and tradable from day one.',
        description: 'Designated market maker callout body',
      }),
    },
    {
      kind: 'features',
      eyebrow: translate({
        id: 'pages.ideas.designatedMm.covers.eyebrow',
        message: 'The commitment',
        description: 'Designated market maker section eyebrow',
      }),
      title: translate({
        id: 'pages.ideas.designatedMm.covers.title',
        message: 'What a designated market maker arrangement typically covers',
        description: 'Designated market maker section title',
      }),
      columns: 2,
      items: [
        {
          icon: '↔️',
          title: translate({
            id: 'pages.ideas.designatedMm.covers.spread.title',
            message: 'Maximum spread',
            description: 'Designated market maker feature title',
          }),
          description: translate({
            id: 'pages.ideas.designatedMm.covers.spread.description',
            message:
              'A cap on how wide the gap between best bid and best ask is allowed to be — the headline measure of how tradable the book is.',
            description: 'Designated market maker feature description',
          }),
        },
        {
          icon: '📚',
          title: translate({
            id: 'pages.ideas.designatedMm.covers.depth.title',
            message: 'Minimum depth',
            description: 'Designated market maker feature title',
          }),
          description: translate({
            id: 'pages.ideas.designatedMm.covers.depth.description',
            message:
              'A floor on the size resting on each side, often within a price band, so larger orders can fill without slippage spikes.',
            description: 'Designated market maker feature description',
          }),
        },
        {
          icon: '⏱️',
          title: translate({
            id: 'pages.ideas.designatedMm.covers.uptime.title',
            message: 'Quoting uptime',
            description: 'Designated market maker feature title',
          }),
          description: translate({
            id: 'pages.ideas.designatedMm.covers.uptime.description',
            message:
              'A required share of time the quotes must be live — the difference between liquidity that is there when traders arrive and liquidity that is not.',
            description: 'Designated market maker feature description',
          }),
        },
        {
          icon: '📊',
          title: translate({
            id: 'pages.ideas.designatedMm.covers.reporting.title',
            message: 'Reporting',
            description: 'Designated market maker feature title',
          }),
          description: translate({
            id: 'pages.ideas.designatedMm.covers.reporting.description',
            message:
              'Regular evidence that the spread, depth and uptime targets were actually met, so the project and exchange can verify the commitment.',
            description: 'Designated market maker feature description',
          }),
        },
      ],
    },
    {
      kind: 'stats',
      eyebrow: translate({
        id: 'pages.ideas.designatedMm.stats.eyebrow',
        message: 'The shape of it',
        description: 'Designated market maker section eyebrow',
      }),
      title: translate({
        id: 'pages.ideas.designatedMm.stats.title',
        message: 'What a designated mandate looks like in practice',
        description: 'Designated market maker section title',
      }),
      items: [
        {
          value: translate({
            id: 'pages.ideas.designatedMm.stats.sided.value',
            message: 'Two-sided',
            description: 'Designated market maker stat value',
          }),
          label: translate({
            id: 'pages.ideas.designatedMm.stats.sided.label',
            message: 'Quotes on both bid and ask, not just one side',
            description: 'Designated market maker stat label',
          }),
        },
        {
          value: translate({
            id: 'pages.ideas.designatedMm.stats.uptime.value',
            message: 'Agreed uptime',
            description: 'Designated market maker stat value',
          }),
          label: translate({
            id: 'pages.ideas.designatedMm.stats.uptime.label',
            message: 'A defined share of time the quotes must stay live',
            description: 'Designated market maker stat label',
          }),
          sub: translate({
            id: 'pages.ideas.designatedMm.stats.uptime.sub',
            message: 'set per mandate',
            description: 'Designated market maker stat sub',
          }),
        },
        {
          value: translate({
            id: 'pages.ideas.designatedMm.stats.venues.value',
            message: 'Per venue',
            description: 'Designated market maker stat value',
          }),
          label: translate({
            id: 'pages.ideas.designatedMm.stats.venues.label',
            message: 'Obligations defined for each exchange the token lists on',
            description: 'Designated market maker stat label',
          }),
        },
      ],
    },
    {
      kind: 'faq',
      eyebrow: 'FAQ',
      title: translate({
        id: 'pages.ideas.designatedMm.faq.title',
        message: 'Designated market maker questions',
        description: 'Designated market maker FAQ title',
      }),
      items: [
        {
          question: translate({
            id: 'pages.ideas.designatedMm.faq.q1',
            message: 'Who needs a designated market maker?',
            description: 'Designated market maker FAQ question',
          }),
          answer: translate({
            id: 'pages.ideas.designatedMm.faq.a1',
            message:
              'Projects with a new or recent token listing, and exchanges that want listed pairs to stay tradable. The arrangement gives both sides a clear, measurable liquidity guarantee.',
            description: 'Designated market maker FAQ answer',
          }),
        },
        {
          question: translate({
            id: 'pages.ideas.designatedMm.faq.q2',
            message: 'Which venues does OctoBot Market Making support?',
            description: 'Designated market maker FAQ question',
          }),
          answer: translate({
            id: 'pages.ideas.designatedMm.faq.a2',
            message:
              'Centralized order-book exchanges. OctoBot Market Making connects through your exchange API keys to quote two-sided liquidity, and never takes custody of funds.',
            description: 'Designated market maker FAQ answer',
          }),
        },
        {
          question: translate({
            id: 'pages.ideas.designatedMm.faq.q3',
            message: 'How are the spread and uptime targets agreed?',
            description: 'Designated market maker FAQ question',
          }),
          answer: translate({
            id: 'pages.ideas.designatedMm.faq.a3',
            message:
              'They are set per mandate, based on the token, the venue and what the exchange expects. Book a call and we will scope the spread, depth and uptime that fit your listing.',
            description: 'Designated market maker FAQ answer',
          }),
        },
      ],
    },
  ],
  cta: {
    title: translate({
      id: 'pages.ideas.designatedMm.cta.title',
      message: 'Need committed liquidity for a listing?',
      description: 'Designated market maker CTA title',
    }),
    description: translate({
      id: 'pages.ideas.designatedMm.cta.description',
      message:
        'OctoBot Market Making quotes two-sided liquidity on centralized order-book venues. Book a call to scope the spread, depth and uptime your token needs.',
      description: 'Designated market maker CTA description',
    }),
    actions: [
      {
        label: translate({
          id: 'pages.ideas.designatedMm.cta.action.contact',
          message: 'Book a call',
          description: 'Designated market maker CTA action label',
        }),
        to: 'mailto:contact@octobot.cloud',
      },
      {
        label: translate({
          id: 'pages.ideas.designatedMm.cta.action.dex',
          message: 'DEX vs order-book market making',
          description: 'Designated market maker CTA action label',
        }),
        to: '/features/ideas/dex-market-making',
        variant: 'ghost',
      },
    ],
  },
};

export default function DesignatedMarketMakerPage(): ReactNode {
  return <IdeaPage data={DATA} />;
}
