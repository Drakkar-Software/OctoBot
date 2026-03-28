import type {ReactNode} from 'react';
import clsx from 'clsx';
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
    title: 'Users',
    icon: '🚀',
    description: (
      <>
        Install, configure, and run OctoBot. Connect exchanges, set up trading
        pairs, manage updates, and monitor your bot through the web interface.
      </>
    ),
    link: '/users/getting-started',
    linkLabel: 'Get Started',
  },
  {
    title: 'Creators',
    icon: '📊',
    description: (
      <>
        Build and customize trading strategies. Configure evaluators, create
        custom tentacles, backtest strategies, and fine-tune trading parameters.
      </>
    ),
    link: '/creators/getting-started',
    linkLabel: 'Create Strategies',
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
    <div className={clsx('col col--4')}>
      <div className={clsx('text--center padding-horiz--md', styles.featureCard)}>
        <div className={styles.featureIcon}>{icon}</div>
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
        <div className={clsx('text--center', styles.sectionHeader)}>
          <Heading as="h2">Choose your path</Heading>
          <p>OctoBot documentation is organized by audience. Pick the guide that fits your needs.</p>
        </div>
        <div className="row">
          {AudienceList.map((props, idx) => (
            <AudienceCard key={idx} {...props} />
          ))}
        </div>
      </div>
    </section>
  );
}
