import type {ReactNode} from 'react';
import Translate, {translate} from '@docusaurus/Translate';
import {IdeaPage, ScheduleVisual, type IdeaPageData} from '@site/src/components/pages/ideas';

/*
 * SEO idea page — route: /features/ideas/dca-bot
 * Angle: explain dollar-cost averaging, then show how OctoBot automates it.
 */

const DATA: IdeaPageData = {
  meta: {
    title: translate({
      id: 'pages.ideas.dcaBot.meta.title',
      message: 'DCA Bot — Automated dollar-cost averaging for crypto',
      description: 'DCA bot page meta title',
    }),
    description: translate({
      id: 'pages.ideas.dcaBot.meta.description',
      message:
        'Automate dollar-cost averaging with OctoBot — schedule recurring crypto buys, smooth out volatility, and keep full custody of your funds.',
      description: 'DCA bot page meta description',
    }),
  },
  hero: {
    eyebrow: translate({
      id: 'pages.ideas.dcaBot.hero.eyebrow',
      message: 'Strategy · Dollar-cost averaging',
      description: 'DCA bot hero eyebrow',
    }),
    title: (
      <Translate
        id="pages.ideas.dcaBot.hero.title"
        description="DCA bot hero title"
        values={{
          accent: (
            <span className="ng-text-gradient">
              {translate({
                id: 'pages.ideas.dcaBot.hero.title.accent',
                message: 'on a schedule.',
                description: 'DCA bot hero title accent',
              })}
            </span>
          ),
        }}>
        {'Buy crypto automatically, {accent}'}
      </Translate>
    ),
    subtitle: translate({
      id: 'pages.ideas.dcaBot.hero.subtitle',
      message:
        'A DCA bot places the same recurring buy for you, day after day — so your average entry price stops depending on when you happened to click. OctoBot runs it on your own exchange account.',
      description: 'DCA bot hero subtitle',
    }),
    actions: [
      {
        label: translate({
          id: 'pages.ideas.dcaBot.hero.action.create',
          message: 'Create your DCA bot',
          description: 'DCA bot hero action label',
        }),
        to: 'https://www.octobot.cloud',
      },
      {
        label: translate({
          id: 'pages.ideas.dcaBot.hero.action.guide',
          message: 'Read the DCA guide',
          description: 'DCA bot hero action label',
        }),
        to: '/guides/octobot',
        variant: 'ghost',
      },
    ],
    visual: (
      <ScheduleVisual
        label={translate({
          id: 'pages.ideas.dcaBot.visual.label',
          message: 'Recurring buys',
          description: 'DCA bot visual label',
        })}
        note="BTC · weekly"
        rows={[
          {date: 'Mon 09:00', detail: 'BTC/USDT', amount: '+ $50'},
          {date: 'Mon 09:00', detail: 'BTC/USDT', amount: '+ $50'},
          {date: 'Mon 09:00', detail: 'BTC/USDT', amount: '+ $50'},
          {date: 'Mon 09:00', detail: 'BTC/USDT', amount: '+ $50'},
        ]}
      />
    ),
  },
  sections: [
    {
      kind: 'callout',
      eyebrow: translate({
        id: 'pages.ideas.dcaBot.what.eyebrow',
        message: 'What it is',
        description: 'DCA bot section eyebrow',
      }),
      title: translate({
        id: 'pages.ideas.dcaBot.what.title',
        message: 'Dollar-cost averaging, without the discipline tax',
        description: 'DCA bot section title',
      }),
      body: translate({
        id: 'pages.ideas.dcaBot.what.body',
        message:
          'Dollar-cost averaging means investing a fixed amount at a fixed interval regardless of price. It works because it removes timing from the decision — but only if you actually stick to it. A DCA bot is the part that sticks to it: it never skips a week because the market looks scary, and never doubles down because it looks exciting.',
        description: 'DCA bot callout body',
      }),
    },
    {
      kind: 'steps',
      eyebrow: translate({
        id: 'pages.ideas.dcaBot.how.eyebrow',
        message: 'How it works',
        description: 'DCA bot section eyebrow',
      }),
      title: translate({
        id: 'pages.ideas.dcaBot.how.title',
        message: 'From idea to recurring buy in three steps',
        description: 'DCA bot section title',
      }),
      items: [
        {
          title: translate({
            id: 'pages.ideas.dcaBot.how.connect.title',
            message: 'Connect your exchange',
            description: 'DCA bot step title',
          }),
          description: translate({
            id: 'pages.ideas.dcaBot.how.connect.description',
            message:
              'Add a read-and-trade API key. Funds stay on your own account — OctoBot never holds them.',
            description: 'DCA bot step description',
          }),
        },
        {
          title: translate({
            id: 'pages.ideas.dcaBot.how.set.title',
            message: 'Set amount and interval',
            description: 'DCA bot step title',
          }),
          description: translate({
            id: 'pages.ideas.dcaBot.how.set.description',
            message:
              'Pick the pair, the buy size and the cadence — hourly, daily, weekly, or your own schedule.',
            description: 'DCA bot step description',
          }),
        },
        {
          title: translate({
            id: 'pages.ideas.dcaBot.how.run.title',
            message: 'Let it run',
            description: 'DCA bot step title',
          }),
          description: translate({
            id: 'pages.ideas.dcaBot.how.run.description',
            message:
              'The bot places each order on time and logs every fill. Pause or adjust it whenever you want.',
            description: 'DCA bot step description',
          }),
        },
      ],
    },
    {
      kind: 'features',
      eyebrow: translate({
        id: 'pages.ideas.dcaBot.why.eyebrow',
        message: 'Why automate it',
        description: 'DCA bot section eyebrow',
      }),
      title: translate({
        id: 'pages.ideas.dcaBot.why.title',
        message: 'What a bot adds over a manual habit',
        description: 'DCA bot section title',
      }),
      items: [
        {
          icon: '📆',
          title: translate({
            id: 'pages.ideas.dcaBot.why.consistency.title',
            message: 'Consistency',
            description: 'DCA bot feature title',
          }),
          description: translate({
            id: 'pages.ideas.dcaBot.why.consistency.description',
            message:
              'Every interval is honoured — no missed weeks, no emotional skips.',
            description: 'DCA bot feature description',
          }),
        },
        {
          icon: '🧮',
          title: translate({
            id: 'pages.ideas.dcaBot.why.average.title',
            message: 'A real average price',
            description: 'DCA bot feature title',
          }),
          description: translate({
            id: 'pages.ideas.dcaBot.why.average.description',
            message:
              'Spreading entries across time flattens the impact of any single volatile day.',
            description: 'DCA bot feature description',
          }),
        },
        {
          icon: '🔀',
          title: translate({
            id: 'pages.ideas.dcaBot.why.combine.title',
            message: 'Combine with signals',
            description: 'DCA bot feature title',
          }),
          description: translate({
            id: 'pages.ideas.dcaBot.why.combine.description',
            message:
              'Layer indicators on top so the bot buys more on dips and less on spikes.',
            description: 'DCA bot feature description',
          }),
        },
        {
          icon: '🔑',
          title: translate({
            id: 'pages.ideas.dcaBot.why.custody.title',
            message: 'Self-custody',
            description: 'DCA bot feature title',
          }),
          description: translate({
            id: 'pages.ideas.dcaBot.why.custody.description',
            message:
              'Open-source and running against your own exchange keys — nothing to trust but the code.',
            description: 'DCA bot feature description',
          }),
        },
      ],
    },
    {
      kind: 'faq',
      eyebrow: 'FAQ',
      title: translate({
        id: 'pages.ideas.dcaBot.faq.title',
        message: 'DCA bot questions',
        description: 'DCA bot FAQ title',
      }),
      items: [
        {
          question: translate({
            id: 'pages.ideas.dcaBot.faq.q1',
            message: 'Is a DCA bot free?',
            description: 'DCA bot FAQ question',
          }),
          answer: translate({
            id: 'pages.ideas.dcaBot.faq.a1',
            message:
              'OctoBot is open source and free to self-host. You only ever pay your exchange its normal trading fees.',
            description: 'DCA bot FAQ answer',
          }),
        },
        {
          question: translate({
            id: 'pages.ideas.dcaBot.faq.q2',
            message: 'Which coins can I DCA into?',
            description: 'DCA bot FAQ question',
          }),
          answer: translate({
            id: 'pages.ideas.dcaBot.faq.a2',
            message:
              'Any trading pair your connected exchange supports — major coins, stablecoins pairs, or smaller markets.',
            description: 'DCA bot FAQ answer',
          }),
        },
        {
          question: translate({
            id: 'pages.ideas.dcaBot.faq.q3',
            message: 'Can I stop or change the schedule later?',
            description: 'DCA bot FAQ question',
          }),
          answer: translate({
            id: 'pages.ideas.dcaBot.faq.a3',
            message:
              'Yes. The schedule, amount and pair are all editable at any time, and the bot can be paused without losing its history.',
            description: 'DCA bot FAQ answer',
          }),
        },
      ],
    },
  ],
  cta: {
    title: translate({
      id: 'pages.ideas.dcaBot.cta.title',
      message: 'Start dollar-cost averaging on autopilot',
      description: 'DCA bot CTA title',
    }),
    description: translate({
      id: 'pages.ideas.dcaBot.cta.description',
      message:
        'Create a free OctoBot, connect your exchange and schedule your first recurring buy.',
      description: 'DCA bot CTA description',
    }),
    actions: [
      {
        label: translate({
          id: 'pages.ideas.dcaBot.cta.action.create',
          message: 'Create your DCA bot',
          description: 'DCA bot CTA action label',
        }),
        to: 'https://www.octobot.cloud',
      },
      {
        label: translate({
          id: 'pages.ideas.dcaBot.cta.action.app',
          message: 'See the OctoBot App',
          description: 'DCA bot CTA action label',
        }),
        to: '/features/octobot-app',
        variant: 'ghost',
      },
    ],
  },
};

export default function DcaBotPage(): ReactNode {
  return <IdeaPage data={DATA} />;
}
