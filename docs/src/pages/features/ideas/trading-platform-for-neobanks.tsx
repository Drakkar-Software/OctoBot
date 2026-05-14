import type {ReactNode} from 'react';
import Translate, {translate} from '@docusaurus/Translate';
import {IdeaPage, DeviceVisual, type IdeaPageData} from '@site/src/components/pages/ideas';

/* SEO idea page — route: /features/ideas/trading-platform-for-neobanks
 * Angle: for neobanks — ship a polished wealth product under your brand, running entirely inside your own VPC and tenancy. */

const DATA: IdeaPageData = {
  meta: {
    title: translate({
      id: 'pages.ideas.forNeobanks.meta.title',
      message: 'Trading platform for neobanks — a wealth product in your VPC',
      description: 'Neobanks page meta title',
    }),
    description: translate({
      id: 'pages.ideas.forNeobanks.meta.description',
      message:
        'Ship a polished trading and wealth product to your users — fully branded, running inside your own VPC and tenancy, with no customer data leaving your perimeter.',
      description: 'Neobanks page meta description',
    }),
  },
  hero: {
    eyebrow: translate({
      id: 'pages.ideas.forNeobanks.hero.eyebrow',
      message: 'For neobanks & fintechs',
      description: 'Neobanks hero eyebrow',
    }),
    title: (
      <Translate
        id="pages.ideas.forNeobanks.hero.title"
        description="Neobanks hero title"
        values={{
          accent: (
            <span className="ng-text-gradient">
              {translate({
                id: 'pages.ideas.forNeobanks.hero.title.accent',
                message: 'inside your own walls.',
                description: 'Neobanks hero title accent',
              })}
            </span>
          ),
        }}>
        {'A wealth product that runs {accent}'}
      </Translate>
    ),
    subtitle: translate({
      id: 'pages.ideas.forNeobanks.hero.subtitle',
      message:
        'Give your users a polished trading and investing experience under your brand — deployed inside your own VPC and tenancy. The product they tap is yours; the data behind it never leaves your perimeter.',
      description: 'Neobanks hero subtitle',
    }),
    actions: [
      {
        label: translate({
          id: 'pages.ideas.forNeobanks.hero.action.demo',
          message: 'Book a demo',
          description: 'Neobanks hero action label',
        }),
        to: 'mailto:contact@octobot.cloud',
      },
      {
        label: translate({
          id: 'pages.ideas.forNeobanks.hero.action.whitelabel',
          message: 'See the full platform',
          description: 'Neobanks hero action label',
        }),
        to: '/whitelabel',
        variant: 'ghost',
      },
    ],
    visual: (
      <DeviceVisual
        label={translate({
          id: 'pages.ideas.forNeobanks.visual.label',
          message: 'Your app',
          description: 'Neobanks visual label',
        })}
        note={translate({
          id: 'pages.ideas.forNeobanks.visual.note',
          message: 'your brand · your tenancy',
          description: 'Neobanks visual note',
        })}
        lines={[
          {width: 70, accent: true},
          {width: 95},
          {width: 88},
          {width: 60},
          {width: 92},
        ]}
        cta={translate({
          id: 'pages.ideas.forNeobanks.visual.cta',
          message: 'Invest',
          description: 'Neobanks visual cta',
        })}
      />
    ),
  },
  sections: [
    {
      kind: 'icons',
      columns: 2,
      eyebrow: translate({
        id: 'pages.ideas.forNeobanks.needs.eyebrow',
        message: 'What matters to a neobank',
        description: 'Neobanks section eyebrow',
      }),
      title: translate({
        id: 'pages.ideas.forNeobanks.needs.title',
        message: 'A trading feature your users — and your CISO — can trust',
        description: 'Neobanks section title',
      }),
      lead: translate({
        id: 'pages.ideas.forNeobanks.needs.lead',
        message:
          'Adding investing to a banking app is a product decision and a compliance decision at once. The platform has to satisfy both.',
        description: 'Neobanks section lead',
      }),
      items: [
        {
          icon: '🎨',
          text: translate({
            id: 'pages.ideas.forNeobanks.needs.brand',
            message:
              'Fully branded frontend — a polished web and mobile experience your users see as a native part of your app.',
            description: 'Neobanks icon item',
          }),
        },
        {
          icon: '☁️',
          text: translate({
            id: 'pages.ideas.forNeobanks.needs.vpc',
            message:
              'Runs in your VPC and tenancy — deployed alongside the rest of your stack, on infrastructure you already operate.',
            description: 'Neobanks icon item',
          }),
        },
        {
          icon: '🛡️',
          text: translate({
            id: 'pages.ideas.forNeobanks.needs.data',
            message:
              'No data leaves your perimeter — customer balances, orders and identity stay inside your own boundary.',
            description: 'Neobanks icon item',
          }),
        },
        {
          icon: '🔑',
          text: translate({
            id: 'pages.ideas.forNeobanks.needs.auth',
            message:
              'Your auth, your accounts — the platform plugs into your existing identity and user model rather than replacing it.',
            description: 'Neobanks icon item',
          }),
        },
      ],
    },
    {
      kind: 'callout',
      variant: 'strong',
      eyebrow: translate({
        id: 'pages.ideas.forNeobanks.full.eyebrow',
        message: 'The whole picture',
        description: 'Neobanks section eyebrow',
      }),
      title: translate({
        id: 'pages.ideas.forNeobanks.full.title',
        message: 'Frontend modes, deployment and the security model',
        description: 'Neobanks section title',
      }),
      body: (
        <Translate
          id="pages.ideas.forNeobanks.full.body"
          description="Neobanks callout body"
          values={{
            link: (
              <a href="/whitelabel">
                {translate({
                  id: 'pages.ideas.forNeobanks.full.body.link',
                  message: 'the OctoBot Whitelabel page',
                  description: 'Neobanks callout link text',
                })}
              </a>
            ),
          }}>
          {
            'OctoBot is open source, and the whitelabel platform ships as an embeddable widget, a full web app or native mobile — all deployed in your own infrastructure. For the frontend options, deployment path and security model, see {link}.'
          }
        </Translate>
      ),
    },
    {
      kind: 'faq',
      eyebrow: 'FAQ',
      title: translate({
        id: 'pages.ideas.forNeobanks.faq.title',
        message: 'Neobank questions',
        description: 'Neobanks FAQ title',
      }),
      items: [
        {
          question: translate({
            id: 'pages.ideas.forNeobanks.faq.q1',
            message: 'Does customer data ever leave our environment?',
            description: 'Neobanks FAQ question',
          }),
          answer: translate({
            id: 'pages.ideas.forNeobanks.faq.a1',
            message:
              'No. The platform runs inside your VPC and tenancy, so balances, orders and user identity stay within your own perimeter. There is no SaaS layer and no telemetry.',
            description: 'Neobanks FAQ answer',
          }),
        },
        {
          question: translate({
            id: 'pages.ideas.forNeobanks.faq.q2',
            message: 'How branded can the user-facing product be?',
            description: 'Neobanks FAQ question',
          }),
          answer: translate({
            id: 'pages.ideas.forNeobanks.faq.a2',
            message:
              'Fully. The frontend ships as a widget, a web app or native mobile source — all yours to theme so it feels like part of your app rather than a third-party bolt-on.',
            description: 'Neobanks FAQ answer',
          }),
        },
        {
          question: translate({
            id: 'pages.ideas.forNeobanks.faq.q3',
            message: 'Can our security team review it before launch?',
            description: 'Neobanks FAQ question',
          }),
          answer: translate({
            id: 'pages.ideas.forNeobanks.faq.a3',
            message:
              'Yes. OctoBot is open source and the whitelabel platform ships with source, so your security team can audit the code and run it through your own review process.',
            description: 'Neobanks FAQ answer',
          }),
        },
      ],
    },
  ],
  cta: {
    title: translate({
      id: 'pages.ideas.forNeobanks.cta.title',
      message: 'Add investing to your app — without giving up control',
      description: 'Neobanks CTA title',
    }),
    description: translate({
      id: 'pages.ideas.forNeobanks.cta.description',
      message:
        'Book a demo and we’ll walk through the branded frontend, the deployment into your VPC and how the data perimeter holds.',
      description: 'Neobanks CTA description',
    }),
    actions: [
      {
        label: translate({
          id: 'pages.ideas.forNeobanks.cta.action.demo',
          message: 'Book a demo',
          description: 'Neobanks CTA action label',
        }),
        to: 'mailto:contact@octobot.cloud',
      },
      {
        label: translate({
          id: 'pages.ideas.forNeobanks.cta.action.whitelabel',
          message: 'See the full platform',
          description: 'Neobanks CTA action label',
        }),
        to: '/whitelabel',
        variant: 'ghost',
      },
    ],
  },
};

export default function ForNeobanksPage(): ReactNode {
  return <IdeaPage data={DATA} />;
}
