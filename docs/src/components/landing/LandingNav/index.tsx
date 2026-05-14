import React, {type ReactNode} from 'react';
import Link from '@docusaurus/Link';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import useBaseUrl from '@docusaurus/useBaseUrl';
import {translate} from '@docusaurus/Translate';
import styles from './styles.module.css';

export interface LandingNavLink {
  label: string;
  to: string;
}

interface LandingNavProps {
  links?: LandingNavLink[];
  /** Primary CTA shown at the right of the nav. */
  cta?: {label: string; to: string};
}

const DEFAULT_LINKS: LandingNavLink[] = [
  {label: 'OctoBot App', to: '/'},
  {
    label: translate({
      id: 'nav.menu.marketMaking',
      message: 'Market Making',
      description: 'Nav menu link label',
    }),
    to: '/market-making',
  },
  {
    label: translate({
      id: 'nav.menu.whitelabel',
      message: 'Whitelabel',
      description: 'Nav menu link label',
    }),
    to: '/whitelabel',
  },
  {
    label: translate({
      id: 'nav.menu.guides',
      message: 'Guides',
      description: 'Nav menu link label',
    }),
    to: '/guides/octobot',
  },
];

const DEFAULT_CTA = {
  label: translate({
    id: 'nav.cta.openOctobotCloud',
    message: 'Open OctoBot Cloud',
    description: 'Nav primary CTA label',
  }),
  to: 'https://www.octobot.cloud',
};

/**
 * Minimal frosted-glass nav for standalone landing pages — replaces the docs
 * navbar with a marketing-style header. Logo links home; CTA on the right.
 */
export default function LandingNav({
  links = DEFAULT_LINKS,
  cta = DEFAULT_CTA,
}: LandingNavProps): ReactNode {
  const {siteConfig} = useDocusaurusContext();
  const logo = useBaseUrl('/img/logo-dark-512.png');

  return (
    <header className={styles.nav}>
      <div className={styles.inner}>
        <Link to="/" className={styles.brand}>
          <img src={logo} alt="" className={styles.logo} />
          <span className={styles.brandName}>{siteConfig.title}</span>
        </Link>

        <nav className={styles.links}>
          {links.map((link) => (
            <Link key={link.to} to={link.to} className={styles.link}>
              {link.label}
            </Link>
          ))}
        </nav>

        <Link to={cta.to} className={`ng-btn ng-btn--primary ${styles.cta}`}>
          {cta.label}
        </Link>
      </div>
    </header>
  );
}
