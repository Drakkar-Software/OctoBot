import type {ReactNode} from 'react';
import Translate, {translate} from '@docusaurus/Translate';
import {IdeaPage, CodeVisual, type IdeaPageData} from '@site/src/components/pages/ideas';

/* SEO idea page — route: /features/ideas/trading-platform-for-asset-managers
 * Angle: for asset managers — operate the whole trading stack yourself, own the SDK, execution and terminal, no vendor in the hot path. */

const DATA: IdeaPageData = {
  meta: {
    title: translate({
      id: 'pages.ideas.forAssetManagers.meta.title',
      message: 'Trading platform for asset managers — own the whole stack',
      description: 'Asset managers page meta title',
    }),
    description: translate({
      id: 'pages.ideas.forAssetManagers.meta.description',
      message:
        'A trading platform asset managers operate themselves: strategy SDK, execution engine and portfolio terminal, deployed in your own infrastructure with no vendor in the hot path.',
      description: 'Asset managers page meta description',
    }),
  },
  hero: {
    eyebrow: translate({
      id: 'pages.ideas.forAssetManagers.hero.eyebrow',
      message: 'For asset managers',
      description: 'Asset managers hero eyebrow',
    }),
    title: (
      <Translate
        id="pages.ideas.forAssetManagers.hero.title"
        description="Asset managers hero title"
        values={{
          accent: (
            <span className="ng-text-gradient">
              {translate({
                id: 'pages.ideas.forAssetManagers.hero.title.accent',
                message: 'you operate yourself.',
                description: 'Asset managers hero title accent',
              })}
            </span>
          ),
        }}>
        {'A trading stack {accent}'}
      </Translate>
    ),
    subtitle: translate({
      id: 'pages.ideas.forAssetManagers.hero.subtitle',
      message:
        'Strategy SDK, execution engine and portfolio terminal — running in your own infrastructure, against your own venue accounts. No vendor sits between your signal and the market, and the source is yours to read.',
      description: 'Asset managers hero subtitle',
    }),
    actions: [
      {
        label: translate({
          id: 'pages.ideas.forAssetManagers.hero.action.demo',
          message: 'Book a demo',
          description: 'Asset managers hero action label',
        }),
        to: 'mailto:contact@octobot.cloud',
      },
      {
        label: translate({
          id: 'pages.ideas.forAssetManagers.hero.action.whitelabel',
          message: 'See the full platform',
          description: 'Asset managers hero action label',
        }),
        to: '/whitelabel',
        variant: 'ghost',
      },
    ],
    visual: (
      <CodeVisual
        label={translate({
          id: 'pages.ideas.forAssetManagers.visual.label',
          message: 'strategy_sdk',
          description: 'Asset managers visual label',
        })}
        note="your_alpha.py"
        lines={[
          {comment: '# your model, your code — runs in your cluster'},
          'class MomentumBook(Strategy):',
          '    def on_candle(self, market):',
          '        signal = self.model.score(market)',
          '        self.execution.rebalance(signal)',
          {comment: '# execution engine routes to your venue accounts'},
        ]}
      />
    ),
  },
  sections: [
    {
      kind: 'icons',
      columns: 2,
      eyebrow: translate({
        id: 'pages.ideas.forAssetManagers.needs.eyebrow',
        message: 'What you actually need',
        description: 'Asset managers section eyebrow',
      }),
      title: translate({
        id: 'pages.ideas.forAssetManagers.needs.title',
        message: 'Built for desks that want to own their stack',
        description: 'Asset managers section title',
      }),
      lead: translate({
        id: 'pages.ideas.forAssetManagers.needs.lead',
        message:
          'When you run other people’s capital, the trading platform is part of your operation — not a black box you rent.',
        description: 'Asset managers section lead',
      }),
      items: [
        {
          icon: '🧩',
          text: translate({
            id: 'pages.ideas.forAssetManagers.needs.sdk',
            message:
              'Strategy SDK you control — express your own models in code, version them, and review every line.',
            description: 'Asset managers icon item',
          }),
        },
        {
          icon: '⇄',
          text: translate({
            id: 'pages.ideas.forAssetManagers.needs.execution',
            message:
              'Execution engine with no vendor in the hot path — orders go straight from your logic to your venue accounts.',
            description: 'Asset managers icon item',
          }),
        },
        {
          icon: '📊',
          text: translate({
            id: 'pages.ideas.forAssetManagers.needs.terminal',
            message:
              'Portfolio terminal for positions, P&L and risk — the same data your team and your auditors see.',
            description: 'Asset managers icon item',
          }),
        },
        {
          icon: '🔒',
          text: translate({
            id: 'pages.ideas.forAssetManagers.needs.airgapped',
            message:
              'Air-gapped deployment supported — run the whole platform on infrastructure that never phones home.',
            description: 'Asset managers icon item',
          }),
        },
      ],
    },
    {
      kind: 'callout',
      variant: 'strong',
      eyebrow: translate({
        id: 'pages.ideas.forAssetManagers.full.eyebrow',
        message: 'The whole picture',
        description: 'Asset managers section eyebrow',
      }),
      title: translate({
        id: 'pages.ideas.forAssetManagers.full.title',
        message: 'Deployment, licensing and the full architecture',
        description: 'Asset managers section title',
      }),
      body: (
        <Translate
          id="pages.ideas.forAssetManagers.full.body"
          description="Asset managers callout body"
          values={{
            link: (
              <a href="/whitelabel">
                {translate({
                  id: 'pages.ideas.forAssetManagers.full.body.link',
                  message: 'the OctoBot Whitelabel page',
                  description: 'Asset managers callout link text',
                })}
              </a>
            ),
          }}>
          {
            'OctoBot is open source, and the whitelabel platform deploys entirely in your own infrastructure — Helm, Terraform or bare metal. For the engine breakdown, frontend options, commercials and security model, see {link}.'
          }
        </Translate>
      ),
    },
    {
      kind: 'faq',
      eyebrow: 'FAQ',
      title: translate({
        id: 'pages.ideas.forAssetManagers.faq.title',
        message: 'Asset manager questions',
        description: 'Asset managers FAQ title',
      }),
      items: [
        {
          question: translate({
            id: 'pages.ideas.forAssetManagers.faq.q1',
            message: 'Can we run our own proprietary strategies?',
            description: 'Asset managers FAQ question',
          }),
          answer: translate({
            id: 'pages.ideas.forAssetManagers.faq.a1',
            message:
              'Yes. The strategy SDK is the intended way to express your own models — your code runs inside your deployment, and nothing about it is shared back.',
            description: 'Asset managers FAQ answer',
          }),
        },
        {
          question: translate({
            id: 'pages.ideas.forAssetManagers.faq.q2',
            message: 'Does any order flow pass through OctoBot servers?',
            description: 'Asset managers FAQ question',
          }),
          answer: translate({
            id: 'pages.ideas.forAssetManagers.faq.a2',
            message:
              'No. The execution engine runs in your infrastructure and connects directly to your venue accounts. There is no vendor in the hot path.',
            description: 'Asset managers FAQ answer',
          }),
        },
        {
          question: translate({
            id: 'pages.ideas.forAssetManagers.faq.q3',
            message: 'Can it run air-gapped for compliance?',
            description: 'Asset managers FAQ question',
          }),
          answer: translate({
            id: 'pages.ideas.forAssetManagers.faq.a3',
            message:
              'Air-gapped deployment is supported. The platform ships with source, so your team can audit it before it ever touches capital.',
            description: 'Asset managers FAQ answer',
          }),
        },
      ],
    },
  ],
  cta: {
    title: translate({
      id: 'pages.ideas.forAssetManagers.cta.title',
      message: 'Run the trading stack on your own terms',
      description: 'Asset managers CTA title',
    }),
    description: translate({
      id: 'pages.ideas.forAssetManagers.cta.description',
      message:
        'Book a demo and we’ll walk through the SDK, the execution engine and how it deploys into your infrastructure.',
      description: 'Asset managers CTA description',
    }),
    actions: [
      {
        label: translate({
          id: 'pages.ideas.forAssetManagers.cta.action.demo',
          message: 'Book a demo',
          description: 'Asset managers CTA action label',
        }),
        to: 'mailto:contact@octobot.cloud',
      },
      {
        label: translate({
          id: 'pages.ideas.forAssetManagers.cta.action.whitelabel',
          message: 'See the full platform',
          description: 'Asset managers CTA action label',
        }),
        to: '/whitelabel',
        variant: 'ghost',
      },
    ],
  },
};

export default function ForAssetManagersPage(): ReactNode {
  return <IdeaPage data={DATA} />;
}
