import type {ReactNode} from 'react';
import Link from '@docusaurus/Link';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import Layout from '@theme/Layout';
import HomepageFeatures from '@site/src/components/HomepageFeatures';
import Heading from '@theme/Heading';

import styles from './index.module.css';

function HomepageHeader() {
  const {siteConfig} = useDocusaurusContext();
  return (
    <header className={`bg-halo-subtle ${styles.heroBanner}`}>
      <div className={`container ${styles.heroInner}`}>
        <span className="ng-eyebrow">Open-source crypto trading</span>
        <Heading as="h1" className={styles.heroTitle}>
          {siteConfig.title}
        </Heading>
        <p className={styles.heroSubtitle}>{siteConfig.tagline}</p>
        <div className={styles.buttons}>
          <Link className="ng-btn ng-btn--primary" to="/guides/octobot">
            I want to use OctoBot
          </Link>
          <Link className="ng-btn ng-btn--ghost" to="/investing/introduction">
            I want to use OctoBot Cloud
          </Link>
          <Link className="ng-btn ng-btn--surface" to="/developers/getting-started">
            I want to contribute
          </Link>
        </div>
      </div>
    </header>
  );
}

export default function Home(): ReactNode {
  return (
    <Layout
      title="Home"
      description="OctoBot is an open-source cryptocurrency trading bot. Guides for users, creators, and developers.">
      <HomepageHeader />
      <main>
        <HomepageFeatures />
      </main>
    </Layout>
  );
}
