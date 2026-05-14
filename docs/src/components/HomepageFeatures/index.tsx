import type {ReactNode} from 'react';
import Heading from '@theme/Heading';
import GlassCard from '@site/src/components/GlassCard';
import styles from './styles.module.css';

type AudienceItem = {
  title: string;
  icon: string;
  description: ReactNode;
  link: string;
  linkLabel: string;
};

const AudienceList: AudienceItem[] = [
  {
    title: 'Open Source',
    icon: '🚀',
    description: (
      <>
        Install, configure, and run OctoBot. Connect exchanges, set up trading
        pairs, manage updates, and monitor your bot through the web interface.
      </>
    ),
    link: '/guides/octobot',
    linkLabel: 'Get Started',
  },
  {
    title: 'OctoBot Cloud',
    icon: '☁️',
    description: (
      <>
        Invest with OctoBot Cloud automated strategies. Follow strategies,
        connect exchanges, and automate TradingView alerts.
      </>
    ),
    link: '/investing/introduction',
    linkLabel: 'Explore Cloud',
  },
  {
    title: 'Developers',
    icon: '🛠️',
    description: (
      <>
        Contribute to the OctoBot codebase. Understand the architecture,
        explore packages, set up your dev environment, and submit pull requests.
      </>
    ),
    link: '/developers/getting-started',
    linkLabel: 'Start Contributing',
  },
];

function AudienceCard({title, icon, description, link, linkLabel}: AudienceItem) {
  return (
    <GlassCard variant="strong" to={link} className={styles.card}>
      <div className={`ng-icon-circle ${styles.icon}`} aria-hidden="true">
        {icon}
      </div>
      <Heading as="h3" className={styles.cardTitle}>
        {title}
      </Heading>
      <p className={styles.cardBody}>{description}</p>
      <span className={styles.cardLink}>
        {linkLabel}
        <span aria-hidden="true" className={styles.arrow}>
          →
        </span>
      </span>
    </GlassCard>
  );
}

export default function HomepageFeatures(): ReactNode {
  return (
    <section className={styles.features}>
      <div className="container">
        <div className={styles.sectionHeader}>
          <span className="ng-eyebrow">Documentation</span>
          <Heading as="h2" className={styles.sectionTitle}>
            Choose your path
          </Heading>
          <p className={styles.sectionLead}>
            OctoBot documentation is organized by audience. Pick the guide that
            fits your needs.
          </p>
        </div>
        <div className={styles.grid}>
          {AudienceList.map((props) => (
            <AudienceCard key={props.title} {...props} />
          ))}
        </div>
      </div>
    </section>
  );
}
