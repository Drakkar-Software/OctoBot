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
    <header className={`hero hero--primary ${styles.heroBanner}`}>
      <div className="container">
        <Heading as="h1" className="hero__title">
          {siteConfig.title}
        </Heading>
        <p className="hero__subtitle">{siteConfig.tagline}</p>
        <div className={styles.buttons}>
          <Link
            className="button button--secondary button--lg"
            to="/guides/octobot">
            I want to use OctoBot
          </Link>
          <Link
            className="button button--outline button--secondary button--lg"
            to="/investing/introduction">
            I want to use OctoBot Cloud
          </Link>
          <Link
            className="button button--outline button--secondary button--lg"
            to="/developers/getting-started">
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
