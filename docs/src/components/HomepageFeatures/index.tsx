import type {ReactNode} from 'react';
import Link from '@docusaurus/Link';
import Heading from '@theme/Heading';
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
    <div className="col col--4">
      <div className={`text--center padding-horiz--md ${styles.featureCard}`}>
        <div className={styles.featureIcon} aria-hidden="true">{icon}</div>
        <Heading as="h3">{title}</Heading>
        <p>{description}</p>
        <Link className="button button--primary button--md" to={link}>
          {linkLabel}
        </Link>
      </div>
    </div>
  );
}

export default function HomepageFeatures(): ReactNode {
  return (
    <section className={styles.features}>
      <div className="container">
        <div className={`text--center ${styles.sectionHeader}`}>
          <Heading as="h2">Choose your path</Heading>
          <p>OctoBot documentation is organized by audience. Pick the guide that fits your needs.</p>
        </div>
        <div className="row">
          {AudienceList.map((props) => (
            <AudienceCard key={props.title} {...props} />
          ))}
        </div>
      </div>
    </section>
  );
}
