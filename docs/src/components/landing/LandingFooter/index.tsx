import React, {type ReactNode} from 'react';
import Link from '@docusaurus/Link';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import Translate, {translate} from '@docusaurus/Translate';
import styles from './styles.module.css';

interface FooterColumn {
  title: string;
  links: {label: string; to: string}[];
}

const COLUMNS: FooterColumn[] = [
  {
    title: translate({
      id: 'nav.footer.product.title',
      message: 'Product',
      description: 'Footer section title',
    }),
    links: [
      {
        label: translate({
          id: 'nav.footer.product.features',
          message: 'Features',
          description: 'Footer link label',
        }),
        to: '/features/strategy-designer',
      },
      {
        label: translate({
          id: 'nav.footer.product.useCases',
          message: 'Use cases',
          description: 'Footer link label',
        }),
        to: '/features/ideas',
      },
      {label: 'OctoBot Cloud', to: 'https://www.octobot.cloud'},
      {
        label: translate({
          id: 'nav.footer.product.blog',
          message: 'Blog',
          description: 'Footer link label',
        }),
        to: '/blog',
      },
    ],
  },
  {
    title: translate({
      id: 'nav.footer.documentation.title',
      message: 'Documentation',
      description: 'Footer section title',
    }),
    links: [
      {
        label: translate({
          id: 'nav.footer.documentation.guides',
          message: 'Guides',
          description: 'Footer link label',
        }),
        to: '/guides/octobot',
      },
      {
        label: translate({
          id: 'nav.footer.documentation.developers',
          message: 'Developers',
          description: 'Footer link label',
        }),
        to: '/developers/getting-started',
      },
      {label: 'OctoBot Script', to: '/octobot-script/getting-started'},
    ],
  },
  {
    title: translate({
      id: 'nav.footer.community.title',
      message: 'Community',
      description: 'Footer section title',
    }),
    links: [
      {label: 'Discord', to: 'https://discord.gg/vHkcb8W'},
      {label: 'Telegram', to: 'https://t.me/OctoBot_Project'},
      {label: 'GitHub', to: 'https://github.com/Drakkar-Software/OctoBot'},
    ],
  },
];

/** Marketing footer for standalone landing pages. */
export default function LandingFooter(): ReactNode {
  const {siteConfig} = useDocusaurusContext();
  const year = new Date().getFullYear();

  return (
    <footer className={styles.footer}>
      <div className={styles.inner}>
        <div className={styles.brandCol}>
          <span className={styles.brandName}>{siteConfig.title}</span>
          <p className={styles.tagline}>{siteConfig.tagline}</p>
        </div>
        <div className={styles.columns}>
          {COLUMNS.map((col) => (
            <div key={col.title} className={styles.column}>
              <span className="ng-eyebrow">{col.title}</span>
              {col.links.map((link) => (
                <Link key={link.to} to={link.to} className={styles.link}>
                  {link.label}
                </Link>
              ))}
            </div>
          ))}
        </div>
      </div>
      <div className={styles.bottom}>
        <Translate
          id="nav.footer.copyright"
          description="Footer copyright line"
          values={{year}}>
          {'Copyright © {year} Drakkar-Software. Built with Docusaurus.'}
        </Translate>
      </div>
    </footer>
  );
}
