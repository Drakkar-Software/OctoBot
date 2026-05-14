import type {ReactNode} from 'react';
import Translate, {translate} from '@docusaurus/Translate';
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
    tag: translate({
      id: 'pages.whitelabel.audience.exchanges.tag',
      message: 'Exchanges',
      description: 'Whitelabel audience tag',
    }),
    title: translate({
      id: 'pages.whitelabel.audience.exchanges.title',
      message: 'Bolt-on automated trading',
      description: 'Whitelabel audience title',
    }),
    text: translate({
      id: 'pages.whitelabel.audience.exchanges.text',
      message:
        'Drop the widget in, or reskin our mobile app. The engine runs next to your matching engine.',
      description: 'Whitelabel audience text',
    }),
    extra: translate({
      id: 'pages.whitelabel.audience.exchanges.extra',
      message: 'Bare-metal · sub-ms co-location',
      description: 'Whitelabel audience extra',
    }),
  },
  {
    tag: translate({
      id: 'pages.whitelabel.audience.neobanks.tag',
      message: 'Neobanks & fintechs',
      description: 'Whitelabel audience tag',
    }),
    title: translate({
      id: 'pages.whitelabel.audience.neobanks.title',
      message: 'Wealth product, fully on-prem',
      description: 'Whitelabel audience title',
    }),
    text: translate({
      id: 'pages.whitelabel.audience.neobanks.text',
      message:
        'A complete trading platform inside your VPC. Helm chart in. Polished app out.',
      description: 'Whitelabel audience text',
    }),
    extra: translate({
      id: 'pages.whitelabel.audience.neobanks.extra',
      message: 'Your cloud · your tenancy',
      description: 'Whitelabel audience extra',
    }),
  },
  {
    tag: translate({
      id: 'pages.whitelabel.audience.assetManagers.tag',
      message: 'Asset managers',
      description: 'Whitelabel audience tag',
    }),
    title: translate({
      id: 'pages.whitelabel.audience.assetManagers.title',
      message: 'Operate, own everything',
      description: 'Whitelabel audience title',
    }),
    text: translate({
      id: 'pages.whitelabel.audience.assetManagers.text',
      message:
        'Strategy SDK, execution engine, PM terminal. No vendor in the hot path.',
      description: 'Whitelabel audience text',
    }),
    extra: translate({
      id: 'pages.whitelabel.audience.assetManagers.extra',
      message: 'Air-gapped supported',
      description: 'Whitelabel audience extra',
    }),
  },
];

const DEPLOY_STEPS: Step[] = [
  {
    title: translate({
      id: 'pages.whitelabel.deploy.provision.title',
      message: 'Provision the engine',
      description: 'Whitelabel deploy step title',
    }),
    description: translate({
      id: 'pages.whitelabel.deploy.provision.description',
      message: 'Helm, Terraform, or bare-metal. Sandbox venues on day one.',
      description: 'Whitelabel deploy step description',
    }),
  },
  {
    title: translate({
      id: 'pages.whitelabel.deploy.frontend.title',
      message: 'Pick a frontend',
      description: 'Whitelabel deploy step title',
    }),
    description: translate({
      id: 'pages.whitelabel.deploy.frontend.description',
      message: 'React/Vue widget, full web fork, or iOS/Android source.',
      description: 'Whitelabel deploy step description',
    }),
  },
  {
    title: translate({
      id: 'pages.whitelabel.deploy.wire.title',
      message: 'Wire venues & users',
      description: 'Whitelabel deploy step title',
    }),
    description: translate({
      id: 'pages.whitelabel.deploy.wire.description',
      message:
        'Your auth, your accounts, your observability. Flip live when ready.',
      description: 'Whitelabel deploy step description',
    }),
  },
  {
    title: translate({
      id: 'pages.whitelabel.deploy.support.title',
      message: 'Source-level support',
      description: 'Whitelabel deploy step title',
    }),
    description: translate({
      id: 'pages.whitelabel.deploy.support.description',
      message: 'Quarterly drops, joint roadmap, direct Slack.',
      description: 'Whitelabel deploy step description',
    }),
  },
];

const PLATFORM: Feature[] = [
  {
    icon: '⌗',
    title: translate({
      id: 'pages.whitelabel.platform.strategy.title',
      message: 'Strategy engine',
      description: 'Whitelabel platform feature title',
    }),
    description: translate({
      id: 'pages.whitelabel.platform.strategy.description',
      message: '30+ templates plus an SDK to ship your own alpha.',
      description: 'Whitelabel platform feature description',
    }),
  },
  {
    icon: '⇄',
    title: translate({
      id: 'pages.whitelabel.platform.execution.title',
      message: 'Execution engine',
      description: 'Whitelabel platform feature title',
    }),
    description: translate({
      id: 'pages.whitelabel.platform.execution.description',
      message: 'Router, position keeper, fees. 24 venues built in.',
      description: 'Whitelabel platform feature description',
    }),
  },
  {
    icon: '▢',
    title: translate({
      id: 'pages.whitelabel.platform.frontend.title',
      message: 'Frontend stack',
      description: 'Whitelabel platform feature title',
    }),
    description: translate({
      id: 'pages.whitelabel.platform.frontend.description',
      message: 'Widget, web, iOS/Android. Yours to theme and ship.',
      description: 'Whitelabel platform feature description',
    }),
  },
  {
    icon: '↯',
    title: translate({
      id: 'pages.whitelabel.platform.risk.title',
      message: 'Risk & audit',
      description: 'Whitelabel platform feature title',
    }),
    description: translate({
      id: 'pages.whitelabel.platform.risk.description',
      message: 'Caps, kill-switches, audit log. Stored in your DB.',
      description: 'Whitelabel platform feature description',
    }),
  },
  {
    icon: '◷',
    title: translate({
      id: 'pages.whitelabel.platform.backtest.title',
      message: 'Backtest engine',
      description: 'Whitelabel platform feature title',
    }),
    description: translate({
      id: 'pages.whitelabel.platform.backtest.description',
      message: '10y tick data, or bring yours. Runs in your cluster.',
      description: 'Whitelabel platform feature description',
    }),
  },
  {
    icon: '⎈',
    title: translate({
      id: 'pages.whitelabel.platform.source.title',
      message: 'Source support',
      description: 'Whitelabel platform feature title',
    }),
    description: translate({
      id: 'pages.whitelabel.platform.source.description',
      message: 'Direct Slack, quarterly drops, runbook reviews.',
      description: 'Whitelabel platform feature description',
    }),
  },
];

const COMMERCIALS = [
  {
    label: translate({
      id: 'pages.whitelabel.commercials.engine.label',
      message: 'Engine license',
      description: 'Whitelabel commercials row label',
    }),
    value: translate({
      id: 'pages.whitelabel.commercials.engine.value',
      message: 'from €60k / yr',
      description: 'Whitelabel commercials row value',
    }),
    frost: false,
  },
  {
    label: translate({
      id: 'pages.whitelabel.commercials.frontend.label',
      message: 'Frontend stack · each',
      description: 'Whitelabel commercials row label',
    }),
    value: '+€20k',
    frost: false,
  },
  {
    label: translate({
      id: 'pages.whitelabel.commercials.escrow.label',
      message: 'Source escrow',
      description: 'Whitelabel commercials row label',
    }),
    value: translate({
      id: 'pages.whitelabel.commercials.escrow.value',
      message: 'included',
      description: 'Whitelabel commercials row value',
    }),
    frost: true,
  },
  {
    label: translate({
      id: 'pages.whitelabel.commercials.setup.label',
      message: 'Setup & co-deployment',
      description: 'Whitelabel commercials row label',
    }),
    value: translate({
      id: 'pages.whitelabel.commercials.setup.value',
      message: 'scoped',
      description: 'Whitelabel commercials row value',
    }),
    frost: false,
  },
];

const SECURITY = [
  translate({
    id: 'pages.whitelabel.security.onPremise',
    message: '100% on-premise · cloud, metal, or air-gapped',
    description: 'Whitelabel security checklist item',
  }),
  translate({
    id: 'pages.whitelabel.security.sourceShipped',
    message: 'Source shipped, container images signed',
    description: 'Whitelabel security checklist item',
  }),
  translate({
    id: 'pages.whitelabel.security.vault',
    message: 'API keys live in your vault',
    description: 'Whitelabel security checklist item',
  }),
  translate({
    id: 'pages.whitelabel.security.pentest',
    message: 'Quarterly external pentest',
    description: 'Whitelabel security checklist item',
  }),
  translate({
    id: 'pages.whitelabel.security.openSource',
    message: 'Open-source core — audit before signing',
    description: 'Whitelabel security checklist item',
  }),
];

export default function WhitelabelPage(): ReactNode {
  return (
    <LandingLayout
      title={translate({
        id: 'pages.whitelabel.meta.title',
        message: 'OctoBot Whitelabel',
        description: 'Whitelabel page metadata title',
      })}
      description={translate({
        id: 'pages.whitelabel.meta.description',
        message:
          'A complete trading platform — engine, execution, frontend — deployed in your infrastructure. Ships as a widget, a web app, or native mobile. Your brand, top to bottom.',
        description: 'Whitelabel page metadata description',
      })}>
      <div className={styles.gridVeil} aria-hidden="true" />

      <Hero
        eyebrow={translate({
          id: 'pages.whitelabel.hero.eyebrow',
          message: 'Whitelabel · on-premise · full-stack',
          description: 'Whitelabel hero eyebrow',
        })}
        title={
          <Translate
            id="pages.whitelabel.hero.title"
            description="Whitelabel hero title"
            values={{
              accent: (
                <span className="ng-text-gradient">
                  {translate({
                    id: 'pages.whitelabel.hero.title.accent',
                    message: 'Our engine.',
                    description: 'Whitelabel hero title accent words',
                  })}
                </span>
              ),
            }}>
            {'Your brand. Your infra. {accent}'}
          </Translate>
        }
        subtitle={translate({
          id: 'pages.whitelabel.hero.subtitle',
          message:
            'A complete trading platform — engine, execution, frontend — deployed in your infra. Ships as a widget, a web app, or native mobile. Your brand top to bottom.',
          description: 'Whitelabel hero subtitle',
        })}
        actions={[
          {
            label: translate({
              id: 'pages.whitelabel.hero.action.demo',
              message: 'Book a demo',
              description: 'Whitelabel hero action label',
            }),
            to: '#contact',
          },
          {
            label: translate({
              id: 'pages.whitelabel.hero.action.api',
              message: 'See the API',
              description: 'Whitelabel hero action label',
            }),
            to: '#deploy',
            variant: 'surface',
          },
        ]}
        visual={<SkinSwitcher />}
        aside={
          <InlineStats
            stats={[
              {
                value: '100%',
                label: translate({
                  id: 'pages.whitelabel.hero.stat.infra',
                  message: 'On your infrastructure',
                  description: 'Whitelabel hero stat label',
                }),
              },
              {
                value: '3',
                label: translate({
                  id: 'pages.whitelabel.hero.stat.modes',
                  message: 'Frontend modes — widget, web, mobile',
                  description: 'Whitelabel hero stat label',
                }),
              },
              {
                value: '0',
                label: translate({
                  id: 'pages.whitelabel.hero.stat.data',
                  message: 'Data ever leaves your perimeter',
                  description: 'Whitelabel hero stat label',
                }),
              },
            ]}
          />
        }
      />

      <Section
        align="left"
        eyebrow={translate({
          id: 'pages.whitelabel.audienceSection.eyebrow',
          message: "01 / Who it's for",
          description: 'Whitelabel section eyebrow',
        })}
        title={
          <Translate
            id="pages.whitelabel.audienceSection.title"
            description="Whitelabel section title"
            values={{
              accent: (
                <span className="ng-text-frost">
                  {translate({
                    id: 'pages.whitelabel.audienceSection.title.accent',
                    message: 'building the product.',
                    description: 'Whitelabel section title accent words',
                  })}
                </span>
              ),
            }}>
            {'Built for the people {accent}'}
          </Translate>
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
        eyebrow={translate({
          id: 'pages.whitelabel.howSection.eyebrow',
          message: '02 / How it works',
          description: 'Whitelabel section eyebrow',
        })}
        title={
          <Translate
            id="pages.whitelabel.howSection.title"
            description="Whitelabel section title"
            values={{
              accent: (
                <span className="ng-text-frost">
                  {translate({
                    id: 'pages.whitelabel.howSection.title.accent',
                    message: 'Run it yours.',
                    description: 'Whitelabel section title accent words',
                  })}
                </span>
              ),
            }}>
            {'Ship the engine. Skin the frontend. {accent}'}
          </Translate>
        }>
        <GlassCard variant="strong" padded className={styles.callout}>
          <Translate
            id="pages.whitelabel.howSection.callout"
            description="Whitelabel how-it-works callout"
            values={{
              strong: (
                <strong>
                  {translate({
                    id: 'pages.whitelabel.howSection.callout.strong',
                    message: 'Three frontends, one engine.',
                    description: 'Whitelabel callout emphasis',
                  })}
                </strong>
              ),
            }}>
            {
              '{strong} Widget, web app, or native mobile — all hitting the same engine in your perimeter.'
            }
          </Translate>
        </GlassCard>
        <StepList steps={DEPLOY_STEPS} />
      </Section>

      <Section
        id="deploy"
        align="right"
        eyebrow={translate({
          id: 'pages.whitelabel.deploySection.eyebrow',
          message: '03 / Deploy it',
          description: 'Whitelabel section eyebrow',
        })}
        title={
          <Translate
            id="pages.whitelabel.deploySection.title"
            description="Whitelabel section title"
            values={{
              accent: (
                <span className="ng-text-frost">
                  {translate({
                    id: 'pages.whitelabel.deploySection.title.accent',
                    message: 'Nothing phones home.',
                    description: 'Whitelabel section title accent words',
                  })}
                </span>
              ),
            }}>
            {'One chart. Your cluster. {accent}'}
          </Translate>
        }>
        <CodeCard />
      </Section>

      <Section
        eyebrow={translate({
          id: 'pages.whitelabel.modesSection.eyebrow',
          message: '04 / Frontend modes',
          description: 'Whitelabel section eyebrow',
        })}
        title={
          <Translate
            id="pages.whitelabel.modesSection.title"
            description="Whitelabel section title"
            values={{
              accent: (
                <span className="ng-text-frost">
                  {translate({
                    id: 'pages.whitelabel.modesSection.title.accent',
                    message: 'Three ways to wear it.',
                    description: 'Whitelabel section title accent words',
                  })}
                </span>
              ),
            }}>
            {'One engine. {accent}'}
          </Translate>
        }>
        <FrontendModes />
        <GlassCard variant="strong" padded className={`${styles.callout} ${styles.calloutAfter}`}>
          <Translate
            id="pages.whitelabel.modesSection.callout"
            description="Whitelabel frontend modes callout"
            values={{
              strong: (
                <strong>
                  {translate({
                    id: 'pages.whitelabel.modesSection.callout.strong',
                    message:
                      'Same engine, same data perimeter for all three.',
                    description: 'Whitelabel callout emphasis',
                  })}
                </strong>
              ),
            }}>
            {'{strong} Pick one — or pick all three.'}
          </Translate>
        </GlassCard>
      </Section>

      <Section
        align="right"
        eyebrow={translate({
          id: 'pages.whitelabel.platformSection.eyebrow',
          message: '05 / What you get',
          description: 'Whitelabel section eyebrow',
        })}
        title={
          <Translate
            id="pages.whitelabel.platformSection.title"
            description="Whitelabel section title"
            values={{
              accent: (
                <span className="ng-text-frost">
                  {translate({
                    id: 'pages.whitelabel.platformSection.title.accent',
                    message: 'in your namespace.',
                    description: 'Whitelabel section title accent words',
                  })}
                </span>
              ),
            }}>
            {'A whole platform, {accent}'}
          </Translate>
        }>
        <FeatureGrid features={PLATFORM} columns={3} />
      </Section>

      <Section>
        <div className={styles.split2}>
          <GlassCard variant="strong" padded={false} className={styles.panel}>
            <span className={styles.panelEyebrow}>
              <Translate
                id="pages.whitelabel.commercials.eyebrow"
                description="Whitelabel panel eyebrow">
                06 / Commercials
              </Translate>
            </span>
            <h3 className={styles.panelTitle}>
              <Translate
                id="pages.whitelabel.commercials.title"
                description="Whitelabel panel title"
                values={{
                  accent: (
                    <span className="ng-text-frost">
                      {translate({
                        id: 'pages.whitelabel.commercials.title.accent',
                        message: 'Source included.',
                        description: 'Whitelabel panel title accent words',
                      })}
                    </span>
                  ),
                }}>
                {'Annual license. {accent}'}
              </Translate>
            </h3>
            <p className={styles.panelSub}>
              <Translate
                id="pages.whitelabel.commercials.sub"
                description="Whitelabel panel sub">
                No per-user metering. No phone-home.
              </Translate>
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
            <span className={styles.panelEyebrow}>
              <Translate
                id="pages.whitelabel.security.eyebrow"
                description="Whitelabel panel eyebrow">
                07 / Security
              </Translate>
            </span>
            <h3 className={styles.panelTitle}>
              <Translate
                id="pages.whitelabel.security.title"
                description="Whitelabel panel title"
                values={{
                  accent: (
                    <span className="ng-text-frost">
                      {translate({
                        id: 'pages.whitelabel.security.title.accent',
                        message: 'your network.',
                        description: 'Whitelabel panel title accent words',
                      })}
                    </span>
                  ),
                }}>
                {'Nothing leaves {accent}'}
              </Translate>
            </h3>
            <p className={styles.panelSub}>
              <Translate
                id="pages.whitelabel.security.sub"
                description="Whitelabel panel sub">
                No SaaS, no telemetry, no multi-tenant.
              </Translate>
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
            <Translate
              id="pages.whitelabel.quote.text"
              description="Whitelabel customer quote"
              values={{
                accent: (
                  <span className="ng-text-frost">
                    {translate({
                      id: 'pages.whitelabel.quote.text.accent',
                      message:
                        'To our regulator, this is just our software.',
                      description: 'Whitelabel customer quote accent',
                    })}
                  </span>
                ),
              }}>
              {
                "It runs in our cluster, compliance can grep the source, the mobile app's in our App Store. {accent}"
              }
            </Translate>
          </p>
          <div className={styles.quoteMeta}>
            <b>
              <Translate
                id="pages.whitelabel.quote.role"
                description="Whitelabel customer quote role">
                Head of Engineering
              </Translate>
            </b>
            <Translate
              id="pages.whitelabel.quote.meta"
              description="Whitelabel customer quote meta">
              {' · Regulated EU broker'}
            </Translate>
          </div>
        </GlassCard>
      </Section>

      <CTABand
        title={
          <Translate
            id="pages.whitelabel.cta.title"
            description="Whitelabel CTA title"
            values={{
              accent: (
                <span className="ng-text-frost">
                  {translate({
                    id: 'pages.whitelabel.cta.title.accent',
                    message: 'Our engine.',
                    description: 'Whitelabel CTA title accent words',
                  })}
                </span>
              ),
            }}>
            {'Your infra. Your brand. {accent}'}
          </Translate>
        }
        description={translate({
          id: 'pages.whitelabel.cta.description',
          message:
            "Book a demo and we'll walk through deployment, theming and the API.",
          description: 'Whitelabel CTA description',
        })}
        actions={[
          {
            label: translate({
              id: 'pages.whitelabel.cta.action.demo',
              message: 'Book a demo',
              description: 'Whitelabel CTA action label',
            }),
            to: 'mailto:contact@octobot.cloud',
          },
          {
            label: translate({
              id: 'pages.whitelabel.cta.action.docs',
              message: 'Developer docs',
              description: 'Whitelabel CTA action label',
            }),
            to: '/developers/getting-started',
            variant: 'ghost',
          },
        ]}
      />
    </LandingLayout>
  );
}
