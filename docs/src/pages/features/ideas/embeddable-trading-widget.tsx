import type {ReactNode} from 'react';
import Translate, {translate} from '@docusaurus/Translate';
import {IdeaPage, CodeVisual, type IdeaPageData} from '@site/src/components/pages/ideas';

/* SEO idea page — route: /features/ideas/embeddable-trading-widget
 * Angle: a drop-in trading widget you embed into your existing product — your users get automated trading without you building a UI. */

const DATA: IdeaPageData = {
  meta: {
    title: translate({
      id: 'pages.ideas.tradingWidget.meta.title',
      message: 'Embeddable Trading Widget — Add automated trading to your app',
      description: 'Trading widget page meta title',
    }),
    description: translate({
      id: 'pages.ideas.tradingWidget.meta.description',
      message:
        'Drop the OctoBot trading widget into your existing site or app. Your users get automated trading, your brand stays on top, and the engine runs in your own infrastructure — no trading UI to build.',
      description: 'Trading widget page meta description',
    }),
  },
  hero: {
    eyebrow: translate({
      id: 'pages.ideas.tradingWidget.hero.eyebrow',
      message: 'Whitelabel · Embeddable widget',
      description: 'Trading widget hero eyebrow',
    }),
    title: (
      <Translate
        id="pages.ideas.tradingWidget.hero.title"
        description="Trading widget hero title"
        values={{
          accent: (
            <span className="ng-text-gradient">
              {translate({
                id: 'pages.ideas.tradingWidget.hero.title.accent',
                message: 'one embed away.',
                description: 'Trading widget hero title accent',
              })}
            </span>
          ),
        }}>
        {'Automated trading in your product, {accent}'}
      </Translate>
    ),
    subtitle: translate({
      id: 'pages.ideas.tradingWidget.hero.subtitle',
      message:
        'The trading widget is a self-contained frontend you drop into a page you already have. Your users configure and run automated strategies inside your product — while the OctoBot engine does the work behind it, in your own infrastructure.',
      description: 'Trading widget hero subtitle',
    }),
    actions: [
      {
        label: translate({
          id: 'pages.ideas.tradingWidget.hero.action.demo',
          message: 'Book a demo',
          description: 'Trading widget hero action label',
        }),
        to: 'mailto:contact@octobot.cloud',
      },
      {
        label: translate({
          id: 'pages.ideas.tradingWidget.hero.action.whitelabel',
          message: 'See whitelabel options',
          description: 'Trading widget hero action label',
        }),
        to: '/whitelabel',
        variant: 'ghost',
      },
    ],
    visual: (
      <CodeVisual
        label={translate({
          id: 'pages.ideas.tradingWidget.visual.label',
          message: 'Drop-in embed',
          description: 'Trading widget visual label',
        })}
        note="your-app.com"
        lines={[
          {comment: '// load the widget once'},
          '<script src="cdn.yourbrand.com/octobot-widget.js">',
          '</script>',
          '',
          {comment: '// mount it wherever you want trading to live'},
          '<octobot-widget',
          '  engine="https://trade.yourbrand.com"',
          '  theme="yourbrand">',
          '</octobot-widget>',
        ]}
      />
    ),
  },
  sections: [
    {
      kind: 'steps',
      eyebrow: translate({
        id: 'pages.ideas.tradingWidget.how.eyebrow',
        message: 'How it works',
        description: 'Trading widget section eyebrow',
      }),
      title: translate({
        id: 'pages.ideas.tradingWidget.how.title',
        message: 'From your page to live trading in three steps',
        description: 'Trading widget section title',
      }),
      items: [
        {
          title: translate({
            id: 'pages.ideas.tradingWidget.how.key.title',
            message: 'Get your key',
            description: 'Trading widget step title',
          }),
          description: translate({
            id: 'pages.ideas.tradingWidget.how.key.description',
            message:
              'Point the widget at your engine deployment and authorize it with a key. The widget talks to your engine — never to us.',
            description: 'Trading widget step description',
          }),
        },
        {
          title: translate({
            id: 'pages.ideas.tradingWidget.how.drop.title',
            message: 'Drop the widget in',
            description: 'Trading widget step title',
          }),
          description: translate({
            id: 'pages.ideas.tradingWidget.how.drop.description',
            message:
              'Add one script tag and one element to a page you already have. No new app, no separate login, no trading screens to design.',
            description: 'Trading widget step description',
          }),
        },
        {
          title: translate({
            id: 'pages.ideas.tradingWidget.how.theme.title',
            message: 'Theme it to match',
            description: 'Trading widget step title',
          }),
          description: translate({
            id: 'pages.ideas.tradingWidget.how.theme.description',
            message:
              'Set your colors, fonts and copy so the widget reads as a native part of your product, not a bolted-on third party.',
            description: 'Trading widget step description',
          }),
        },
      ],
    },
    {
      kind: 'features',
      eyebrow: translate({
        id: 'pages.ideas.tradingWidget.gives.eyebrow',
        message: 'What the widget gives you',
        description: 'Trading widget section eyebrow',
      }),
      title: translate({
        id: 'pages.ideas.tradingWidget.gives.title',
        message: 'A trading surface you ship, not build',
        description: 'Trading widget section title',
      }),
      columns: 2,
      items: [
        {
          icon: '🎨',
          title: translate({
            id: 'pages.ideas.tradingWidget.gives.themable.title',
            message: 'Themable',
            description: 'Trading widget feature title',
          }),
          description: translate({
            id: 'pages.ideas.tradingWidget.gives.themable.description',
            message:
              'Colors, type and copy are configurable, so the widget blends into the page around it instead of standing out.',
            description: 'Trading widget feature description',
          }),
        },
        {
          icon: '⚙️',
          title: translate({
            id: 'pages.ideas.tradingWidget.gives.engine.title',
            message: 'Runs on your engine',
            description: 'Trading widget feature title',
          }),
          description: translate({
            id: 'pages.ideas.tradingWidget.gives.engine.description',
            message:
              'Strategies, orders and exchange connections all run on an OctoBot engine you deploy. The widget is just the window onto it.',
            description: 'Trading widget feature description',
          }),
        },
        {
          icon: '🧩',
          title: translate({
            id: 'pages.ideas.tradingWidget.gives.noui.title',
            message: 'No UI to build',
            description: 'Trading widget feature title',
          }),
          description: translate({
            id: 'pages.ideas.tradingWidget.gives.noui.description',
            message:
              'Strategy configuration, order views and run controls already exist inside the widget — you skip months of frontend work.',
            description: 'Trading widget feature description',
          }),
        },
        {
          icon: '🏷️',
          title: translate({
            id: 'pages.ideas.tradingWidget.gives.brand.title',
            message: 'Your brand',
            description: 'Trading widget feature title',
          }),
          description: translate({
            id: 'pages.ideas.tradingWidget.gives.brand.description',
            message:
              'The widget carries your name and lives at your domain. To your users it is simply a feature of your product.',
            description: 'Trading widget feature description',
          }),
        },
      ],
    },
    {
      kind: 'callout',
      eyebrow: translate({
        id: 'pages.ideas.tradingWidget.where.eyebrow',
        message: 'Where it fits',
        description: 'Trading widget section eyebrow',
      }),
      title: translate({
        id: 'pages.ideas.tradingWidget.where.title',
        message: 'A widget inside what you already have',
        description: 'Trading widget section title',
      }),
      body: translate({
        id: 'pages.ideas.tradingWidget.where.body',
        message:
          'The widget is the right fit when you already own the product and just want to add automated trading to it — a dashboard tab, a portfolio page, a member area. If you want to build a standalone trading app from the ground up rather than embed a piece into an existing one, the app builder route gives you a full reskinnable frontend instead.',
        description: 'Trading widget callout body',
      }),
    },
    {
      kind: 'faq',
      eyebrow: 'FAQ',
      title: translate({
        id: 'pages.ideas.tradingWidget.faq.title',
        message: 'Embeddable widget questions',
        description: 'Trading widget FAQ title',
      }),
      items: [
        {
          question: translate({
            id: 'pages.ideas.tradingWidget.faq.q1',
            message: 'Where does the trading actually run?',
            description: 'Trading widget FAQ question',
          }),
          answer: translate({
            id: 'pages.ideas.tradingWidget.faq.a1',
            message:
              'On an OctoBot engine deployed in your own infrastructure. The widget is a frontend that connects to that engine — strategies, orders and exchange keys all stay on your side.',
            description: 'Trading widget FAQ answer',
          }),
        },
        {
          question: translate({
            id: 'pages.ideas.tradingWidget.faq.q2',
            message: 'Do my users need a separate account?',
            description: 'Trading widget FAQ question',
          }),
          answer: translate({
            id: 'pages.ideas.tradingWidget.faq.a2',
            message:
              'No. The widget is embedded in your product and authorizes against your engine, so users stay within your existing login and account.',
            description: 'Trading widget FAQ answer',
          }),
        },
        {
          question: translate({
            id: 'pages.ideas.tradingWidget.faq.q3',
            message: 'How is this different from the app builder?',
            description: 'Trading widget FAQ question',
          }),
          answer: translate({
            id: 'pages.ideas.tradingWidget.faq.a3',
            message:
              'The widget embeds a piece of automated trading into a product you already run. The app builder is for standing up a full, standalone branded trading app on top of the same engine.',
            description: 'Trading widget FAQ answer',
          }),
        },
      ],
    },
  ],
  cta: {
    title: translate({
      id: 'pages.ideas.tradingWidget.cta.title',
      message: 'Add automated trading without building a UI',
      description: 'Trading widget CTA title',
    }),
    description: translate({
      id: 'pages.ideas.tradingWidget.cta.description',
      message:
        'Book a demo and we will walk through embedding the widget, theming it, and pointing it at an engine in your infrastructure.',
      description: 'Trading widget CTA description',
    }),
    actions: [
      {
        label: translate({
          id: 'pages.ideas.tradingWidget.cta.action.demo',
          message: 'Book a demo',
          description: 'Trading widget CTA action label',
        }),
        to: 'mailto:contact@octobot.cloud',
      },
      {
        label: translate({
          id: 'pages.ideas.tradingWidget.cta.action.whitelabel',
          message: 'See whitelabel options',
          description: 'Trading widget CTA action label',
        }),
        to: '/whitelabel',
        variant: 'ghost',
      },
    ],
  },
};

export default function EmbeddableTradingWidgetPage(): ReactNode {
  return <IdeaPage data={DATA} />;
}
