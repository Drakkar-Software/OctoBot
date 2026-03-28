import {themes as prismThemes} from 'prism-react-renderer';
import type {Config} from '@docusaurus/types';
import type * as Preset from '@docusaurus/preset-classic';

const config: Config = {
  title: 'OctoBot Documentation',
  tagline: 'Open-source cryptocurrency trading bot',
  favicon: 'img/favicon.ico',

  future: {
    v4: true,
  },

  url: 'https://docs.octobot.cloud',
  baseUrl: '/',

  organizationName: 'Drakkar-Software',
  projectName: 'OctoBot',
  trailingSlash: false,

  onBrokenLinks: 'warn',

  i18n: {
    defaultLocale: 'en',
    locales: ['en'],
  },

  headTags: [
    {
      tagName: 'script',
      attributes: {type: 'application/ld+json'},
      innerHTML: JSON.stringify({
        '@context': 'https://schema.org',
        '@type': 'SoftwareApplication',
        name: 'OctoBot',
        applicationCategory: 'FinanceApplication',
        operatingSystem: 'Linux, macOS, Windows, Docker',
        url: 'https://www.octobot.cloud',
        author: {
          '@type': 'Organization',
          name: 'Drakkar-Software',
          url: 'https://github.com/Drakkar-Software',
        },
      }),
    },
  ],

  markdown: {
    format: 'detect',
    hooks: {
      onBrokenMarkdownLinks: 'throw',
    },
  },

  presets: [
    [
      'classic',
      {
        docs: {
          path: 'content',
          routeBasePath: '/',
          sidebarPath: './sidebars.ts',
          editUrl:
            'https://github.com/Drakkar-Software/OctoBot/tree/dev/docs/',
          showLastUpdateTime: true,
          showLastUpdateAuthor: true,
        },
        blog: false,
        theme: {
          customCss: './src/css/custom.css',
        },
        sitemap: {
          priority: 0.5,
          filename: 'sitemap.xml',
        },
      } satisfies Preset.Options,
    ],
  ],

  themeConfig: {
    metadata: [
      {name: 'twitter:card', content: 'summary_large_image'},
      {name: 'twitter:site', content: '@OctoBotTrading'},
      {property: 'og:type', content: 'website'},
      {property: 'og:site_name', content: 'OctoBot Documentation'},
      {name: 'keywords', content: 'octobot, crypto, trading bot, open source, automated trading'},
    ],
    colorMode: {
      defaultMode: 'light',
      respectPrefersColorScheme: true,
    },
    navbar: {
      title: 'OctoBot',
      logo: {
        alt: 'OctoBot Logo',
        src: 'img/logo.svg',
      },
      items: [
        {
          type: 'docSidebar',
          sidebarId: 'users',
          position: 'left',
          label: 'Users',
        },
        {
          type: 'docSidebar',
          sidebarId: 'creators',
          position: 'left',
          label: 'Creators',
        },
        {
          type: 'docSidebar',
          sidebarId: 'developers',
          position: 'left',
          label: 'Developers',
        },
        {
          href: 'https://www.octobot.cloud',
          label: 'OctoBot Cloud',
          position: 'right',
        },
        {
          href: 'https://github.com/Drakkar-Software/OctoBot',
          label: 'GitHub',
          position: 'right',
        },
      ],
    },
    footer: {
      style: 'dark',
      links: [
        {
          title: 'Documentation',
          items: [
            {label: 'Users Guide', to: '/users/getting-started'},
            {label: 'Creators Guide', to: '/creators/getting-started'},
            {label: 'Developers Guide', to: '/developers/getting-started'},
          ],
        },
        {
          title: 'Community',
          items: [
            {
              label: 'Discord',
              href: 'https://discord.gg/vHkcb8W',
            },
            {
              label: 'Telegram',
              href: 'https://t.me/OctoBot_Project',
            },
            {
              label: 'X / Twitter',
              href: 'https://x.com/OctoBotTrading',
            },
          ],
        },
        {
          title: 'More',
          items: [
            {
              label: 'OctoBot Cloud',
              href: 'https://www.octobot.cloud',
            },
            {
              label: 'GitHub',
              href: 'https://github.com/Drakkar-Software/OctoBot',
            },
          ],
        },
      ],
      copyright: `Copyright \u00a9 ${new Date().getFullYear()} Drakkar-Software. Built with Docusaurus.`,
    },
    prism: {
      theme: prismThemes.github,
      darkTheme: prismThemes.dracula,
      additionalLanguages: ['python', 'bash', 'json', 'yaml', 'toml'],
    },
  } satisfies Preset.ThemeConfig,
};

export default config;
