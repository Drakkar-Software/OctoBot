import React, {type ReactNode} from 'react';
import Link from '@docusaurus/Link';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import styles from './styles.module.css';

interface FooterColumn {
  title: string;
  links: {label: string; to: string}[];
}

const COLUMNS: FooterColumn[] = [
  {
    title: 'Product',
    links: [
      {label: 'Features', to: '/features/strategy-designer'},
      {label: 'OctoBot Cloud', to: 'https://www.octobot.cloud'},
      {label: 'Blog', to: '/blog'},
    ],
  },
  {
    title: 'Documentation',
    links: [
      {label: 'Guides', to: '/guides/octobot'},
      {label: 'Developers', to: '/developers/getting-started'},
      {label: 'OctoBot Script', to: '/octobot-script/getting-started'},
    ],
  },
  {
    title: 'Community',
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
        Copyright © {year} Drakkar-Software. Built with Docusaurus.
      </div>
    </footer>
  );
}
