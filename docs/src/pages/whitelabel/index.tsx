import type {ReactNode} from 'react';
import {
  LandingLayout,
  Hero,
  Section,
  FeatureGrid,
  StepList,
  InlineStats,
  CTABand,
  type Feature,
  type Step,
} from '@site/src/components/landing';
import GlassCard from '@site/src/components/GlassCard';
import SkinSwitcher from '@site/src/components/pages/whitelabel/SkinSwitcher';
import CodeCard from '@site/src/components/pages/whitelabel/CodeCard';
import FrontendModes from '@site/src/components/pages/whitelabel/FrontendModes';
import styles from './index.module.css';

/*
 * OctoBot Whitelabel — full custom marketing page, route: /whitelabel.
 *
 * Migrated from the Whitelabel design bundle into the Neo Glass Dark landing
 * toolkit. Built the same way as src/pages/app and src/pages/market-making:
 * a navbar-less LandingLayout composed from reusable components, with bespoke
 * visuals (theme switcher, code card, frontend-mode picker) colocated as
 * underscore-prefixed files Docusaurus ignores as routes.
 */

const AUDIENCE = [
  {
    tag: 'Exchanges',
    title: 'Bolt-on automated trading',
    text: 'Drop the widget in, or reskin our mobile app. The engine runs next to your matching engine.',
    extra: 'Bare-metal · sub-ms co-location',
  },
  {
    tag: 'Neobanks & fintechs',
    title: 'Wealth product, fully on-prem',
    text: 'A complete trading platform inside your VPC. Helm chart in. Polished app out.',
    extra: 'Your cloud · your tenancy',
  },
  {
    tag: 'Asset managers',
    title: 'Operate, own everything',
    text: 'Strategy SDK, execution engine, PM terminal. No vendor in the hot path.',
    extra: 'Air-gapped supported',
  },
];

const DEPLOY_STEPS: Step[] = [
  {
    title: 'Provision the engine',
    description:
      'Helm, Terraform, or bare-metal. Sandbox venues on day one.',
  },
  {
    title: 'Pick a frontend',
    description: 'React/Vue widget, full web fork, or iOS/Android source.',
  },
  {
    title: 'Wire venues & users',
    description:
      'Your auth, your accounts, your observability. Flip live when ready.',
  },
  {
    title: 'Source-level support',
    description: 'Quarterly drops, joint roadmap, direct Slack.',
  },
];

const PLATFORM: Feature[] = [
  {
    icon: '⌗',
    title: 'Strategy engine',
    description: '30+ templates plus an SDK to ship your own alpha.',
  },
  {
    icon: '⇄',
    title: 'Execution engine',
    description: 'Router, position keeper, fees. 24 venues built in.',
  },
  {
    icon: '▢',
    title: 'Frontend stack',
    description: 'Widget, web, iOS/Android. Yours to theme and ship.',
  },
  {
    icon: '↯',
    title: 'Risk & audit',
    description: 'Caps, kill-switches, audit log. Stored in your DB.',
  },
  {
    icon: '◷',
    title: 'Backtest engine',
    description: '10y tick data, or bring yours. Runs in your cluster.',
  },
  {
    icon: '⎈',
    title: 'Source support',
    description: 'Direct Slack, quarterly drops, runbook reviews.',
  },
];

const COMMERCIALS = [
  {label: 'Engine license', value: 'from €60k / yr', frost: false},
  {label: 'Frontend stack · each', value: '+€20k', frost: false},
  {label: 'Source escrow', value: 'included', frost: true},
  {label: 'Setup & co-deployment', value: 'scoped', frost: false},
];

const SECURITY = [
  '100% on-premise · cloud, metal, or air-gapped',
  'Source shipped, container images signed',
  'API keys live in your vault',
  'Quarterly external pentest',
  'Open-source core — audit before signing',
];

export default function WhitelabelPage(): ReactNode {
  return (
    <LandingLayout
      title="OctoBot Whitelabel"
      description="A complete trading platform — engine, execution, frontend — deployed in your infrastructure. Ships as a widget, a web app, or native mobile. Your brand, top to bottom.">
      <div className={styles.gridVeil} aria-hidden="true" />

      <Hero
        eyebrow="Whitelabel · on-premise · full-stack"
        title={
          <>
            Your brand. Your infra.{' '}
            <span className="ng-text-gradient">Our engine.</span>
          </>
        }
        subtitle="A complete trading platform — engine, execution, frontend — deployed in your infra. Ships as a widget, a web app, or native mobile. Your brand top to bottom."
        actions={[
          {label: 'Book a demo', to: '#contact'},
          {label: 'See the API', to: '#deploy', variant: 'surface'},
        ]}
        visual={<SkinSwitcher />}
        aside={
          <InlineStats
            stats={[
              {value: '100%', label: 'On your infrastructure'},
              {value: '3', label: 'Frontend modes — widget, web, mobile'},
              {value: '0', label: 'Data ever leaves your perimeter'},
            ]}
          />
        }
      />

      <Section
        align="left"
        eyebrow="01 / Who it's for"
        title={
          <>
            Built for the people{' '}
            <span className="ng-text-frost">building the product.</span>
          </>
        }>
        <div className={styles.audience}>
          {AUDIENCE.map((aud) => (
            <GlassCard key={aud.tag} padded={false} className={styles.aud}>
              <span className={styles.audTag}>{aud.tag}</span>
              <h3 className={styles.audTitle}>{aud.title}</h3>
              <p className={styles.audText}>{aud.text}</p>
              <div className={styles.audExtra}>{aud.extra}</div>
            </GlassCard>
          ))}
        </div>
      </Section>

      <Section
        id="how"
        align="left"
        eyebrow="02 / How it works"
        title={
          <>
            Ship the engine. Skin the frontend.{' '}
            <span className="ng-text-frost">Run it yours.</span>
          </>
        }>
        <GlassCard variant="strong" padded className={styles.callout}>
          <strong>Three frontends, one engine.</strong> Widget, web app, or
          native mobile — all hitting the same engine in your perimeter.
        </GlassCard>
        <StepList steps={DEPLOY_STEPS} />
      </Section>

      <Section
        id="deploy"
        align="right"
        eyebrow="03 / Deploy it"
        title={
          <>
            One chart. Your cluster.{' '}
            <span className="ng-text-frost">Nothing phones home.</span>
          </>
        }>
        <CodeCard />
      </Section>

      <Section
        eyebrow="04 / Frontend modes"
        title={
          <>
            One engine.{' '}
            <span className="ng-text-frost">Three ways to wear it.</span>
          </>
        }>
        <FrontendModes />
        <GlassCard variant="strong" padded className={`${styles.callout} ${styles.calloutAfter}`}>
          <strong>Same engine, same data perimeter for all three.</strong> Pick
          one — or pick all three.
        </GlassCard>
      </Section>

      <Section
        align="right"
        eyebrow="05 / What you get"
        title={
          <>
            A whole platform,{' '}
            <span className="ng-text-frost">in your namespace.</span>
          </>
        }>
        <FeatureGrid features={PLATFORM} columns={3} />
      </Section>

      <Section>
        <div className={styles.split2}>
          <GlassCard variant="strong" padded={false} className={styles.panel}>
            <span className={styles.panelEyebrow}>06 / Commercials</span>
            <h3 className={styles.panelTitle}>
              Annual license.{' '}
              <span className="ng-text-frost">Source included.</span>
            </h3>
            <p className={styles.panelSub}>
              No per-user metering. No phone-home.
            </p>
            <div className={styles.priceRows}>
              {COMMERCIALS.map((row) => (
                <div key={row.label} className={styles.priceRow}>
                  <span>{row.label}</span>
                  <span
                    className={row.frost ? styles.priceValFrost : styles.priceVal}>
                    {row.value}
                  </span>
                </div>
              ))}
            </div>
          </GlassCard>

          <GlassCard padded={false} className={styles.panel}>
            <span className={styles.panelEyebrow}>07 / Security</span>
            <h3 className={styles.panelTitle}>
              Nothing leaves{' '}
              <span className="ng-text-frost">your network.</span>
            </h3>
            <p className={styles.panelSub}>
              No SaaS, no telemetry, no multi-tenant.
            </p>
            <ul className={styles.checks}>
              {SECURITY.map((item) => (
                <li key={item}>
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </GlassCard>
        </div>
      </Section>

      <Section>
        <GlassCard variant="hero" padded={false} className={styles.quoteCard}>
          <div className={styles.quoteMark} aria-hidden="true">
            &ldquo;
          </div>
          <p className={styles.quoteText}>
            It runs in our cluster, compliance can grep the source, the mobile
            app&apos;s in our App Store.{' '}
            <span className="ng-text-frost">
              To our regulator, this is just our software.
            </span>
          </p>
          <div className={styles.quoteMeta}>
            <b>Head of Engineering</b> · Regulated EU broker
          </div>
        </GlassCard>
      </Section>

      <CTABand
        title={
          <>
            Your infra. Your brand.{' '}
            <span className="ng-text-frost">Our engine.</span>
          </>
        }
        description="Book a demo and we'll walk through deployment, theming and the API."
        actions={[
          {label: 'Book a demo', to: 'mailto:contact@octobot.cloud'},
          {
            label: 'Developer docs',
            to: '/developers/getting-started',
            variant: 'ghost',
          },
        ]}
      />
    </LandingLayout>
  );
}
