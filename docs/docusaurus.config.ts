import {themes as prismThemes} from 'prism-react-renderer';
import type {Config} from '@docusaurus/types';
import type * as Preset from '@docusaurus/preset-classic';

// Neo Glass Dark — DM Sans / DM Mono. Loaded via <link> (non render-blocking)
// instead of an @import in CSS. Preconnect tags are injected through headTags.
const NEO_GLASS_FONTS =
  'https://fonts.googleapis.com/css2?' +
  'family=DM+Sans:ital,opsz,wght@0,9..40,400;0,9..40,500;0,9..40,700;1,9..40,400&' +
  'family=DM+Mono:ital,wght@0,400;0,500;1,400&display=swap';

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
  onBrokenAnchors: 'warn',

  i18n: {
    defaultLocale: 'en',
    locales: ['en', 'fr'],
    localeConfigs: {
      en: {label: 'English', direction: 'ltr'},
      fr: {label: 'Français', direction: 'ltr'},
    },
  },

  stylesheets: [NEO_GLASS_FONTS],

  headTags: [
    {
      tagName: 'link',
      attributes: {rel: 'preconnect', href: 'https://fonts.googleapis.com'},
    },
    {
      tagName: 'link',
      attributes: {
        rel: 'preconnect',
        href: 'https://fonts.gstatic.com',
        crossorigin: 'anonymous',
      },
    },
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

  plugins: [
    [require.resolve('docusaurus-lunr-search'), {
      languages: ['en', 'fr'],
    }],
    // Programmatic SEO pages (per-coin / per-exchange / converter matrix).
    // Fetches its slug list live from the OctoBot Cloud endpoint at build
    // time — no committed fallback, the build fails if it is unreachable.
    require.resolve('./plugins/programmatic-pages'),
    [
      '@docusaurus/plugin-client-redirects',
      {
        redirects: [
          {from: '/guides/developers', to: '/developers/getting-started'},
          {from: '/guides/octobot-developers-environment/setup-your-environment', to: '/developers/environment/setup-your-environment'},
          {from: '/guides/octobot-developers-environment/architecture', to: '/developers/architecture/design-philosophy'},
          {from: '/guides/octobot-developers-environment/environment-variables', to: '/developers/environment/environment-variables'},
          {from: '/guides/octobot-developers-environment/github-repositories', to: '/developers/environment/github-repositories'},
          {from: '/guides/octobot-developers-environment/running-tests', to: '/developers/environment/running-tests'},
          {from: '/guides/octobot-developers-environment/tips', to: '/developers/environment/tips'},
          {from: '/guides/octobot-tentacles-development/create-a-tentacle', to: '/developers/tentacles-dev/create-a-tentacle'},
          {from: '/guides/octobot-tentacles-development/create-a-tentacle-package', to: '/developers/tentacles-dev/create-a-tentacle-package'},
          {from: '/guides/octobot-tentacles-development/customize-your-octobot', to: '/developers/tentacles-dev/customize-your-octobot'},
          {from: '/guides/octobot-script', to: '/octobot-script/getting-started'},
          {from: '/guides/octobot-script-docs/creating-trading-orders', to: '/octobot-script/creating-trading-orders'},
          {from: '/guides/octobot-script-docs/fetching-history', to: '/octobot-script/fetching-history'},
          {from: '/guides/octobot-script-docs/plotting-anything', to: '/octobot-script/plotting-anything'},
          {from: '/guides/octobot-script-docs/plotting-indicators', to: '/octobot-script/plotting-indicators'},
          {from: '/guides/octobot-script-docs/run-report', to: '/octobot-script/run-report'},
          {from: '/guides/octobot-script-docs/strategies', to: '/octobot-script/strategies'},
        ],
        createRedirects(existingPath) {
          // Redirect /guides/octobot-partner-exchanges/<slug> → /guides/exchanges/<slug>
          if (existingPath.startsWith('/guides/exchanges/')) {
            const rest = existingPath.replace('/guides/exchanges/', '');
            return [
              `/guides/octobot-partner-exchanges/${rest}`,
              `/guides/octobot-supported-exchanges/${rest}`,
            ];
          }
          return undefined;
        },
      },
    ],
  ],

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
        blog: {
          path: 'blog',
          routeBasePath: 'blog',
          showReadingTime: true,
          blogTitle: 'OctoBot Blog',
          blogDescription: 'News, updates, and guides from the OctoBot team',
          blogSidebarTitle: 'Recent posts',
          blogSidebarCount: 0,
          postsPerPage: 9,
          onUntruncatedBlogPosts: 'warn',
          feedOptions: {
            type: ['rss', 'atom'],
            title: 'OctoBot Blog',
            description: 'News, updates, and guides from the OctoBot team',
            copyright: `Copyright ${new Date().getFullYear()} Drakkar-Software`,
          },
        },
        theme: {
          // theme-tokens.css holds the Neo Glass Dark design tokens + utility
          // classes; custom.css maps them onto Infima + Docusaurus surfaces.
          customCss: [
            './src/css/theme-tokens.css',
            './src/css/custom.css',
          ],
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
      {name: 'robots', content: 'noindex'},
      {name: 'twitter:card', content: 'summary_large_image'},
      {name: 'twitter:site', content: '@OctoBotTrading'},
      {property: 'og:type', content: 'website'},
      {property: 'og:site_name', content: 'OctoBot Documentation'},
      {name: 'keywords', content: 'octobot, crypto, trading bot, open source, automated trading'},
    ],
    // Neo Glass Dark is a strict dark-mode-only theme — no light palette,
    // so the toggle is disabled and dark is forced.
    colorMode: {
      defaultMode: 'dark',
      disableSwitch: true,
      respectPrefersColorScheme: false,
    },
    navbar: {
      title: 'OctoBot',
      logo: {
        alt: 'OctoBot Logo',
        src: 'img/logo-light-512.png',
        srcDark: 'img/logo-dark-512.png',
      },
      items: [
        {
          type: 'docSidebar',
          sidebarId: 'guides',
          position: 'left',
          label: 'Guides',
        },
        {
          type: 'docSidebar',
          sidebarId: 'investing',
          position: 'left',
          label: 'OctoBot Cloud',
        },
        {
          type: 'docSidebar',
          sidebarId: 'octobot-script',
          position: 'left',
          label: 'OctoBot Script',
        },
        {
          type: 'docSidebar',
          sidebarId: 'market-making',
          position: 'left',
          label: 'Market Making',
        },
        {
          type: 'docSidebar',
          sidebarId: 'developers',
          position: 'left',
          label: 'Developers',
        },
        {
          type: 'localeDropdown',
          position: 'right',
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
            {label: 'Guides', to: '/guides/octobot'},
            {label: 'OctoBot Cloud', to: '/investing/introduction'},
            {label: 'Blog', to: '/blog'},
            {label: 'Developers', to: '/developers/getting-started'},
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
            {
              label: 'Terms of Use',
              to: '/terms',
            },
            {
              label: 'Privacy Policy',
              to: '/terms/privacy',
            },
          ],
        },
      ],
      copyright: `Copyright \u00a9 ${new Date().getFullYear()} Drakkar-Software. Built with Docusaurus.`,
    },
    docs: {
      sidebar: {
        autoCollapseCategories: true,
        hideable: true,
      },
    },
    tableOfContents: {
      minHeadingLevel: 2,
      maxHeadingLevel: 3,
    },
    prism: {
      theme: prismThemes.oneDark,
      darkTheme: prismThemes.oneDark,
      additionalLanguages: ['python', 'bash', 'json', 'yaml', 'toml'],
    },
  } satisfies Preset.ThemeConfig,
};

export default config;
