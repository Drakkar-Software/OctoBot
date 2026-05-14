import React, {useEffect, useRef, type ReactNode} from 'react';
import Translate, {translate} from '@docusaurus/Translate';
import GlassCard from '@site/src/components/GlassCard';
import styles from './WeekTimeline.module.css';

/*
 * Page-local "a week with OctoBot" visual — a stat row plus an animated
 * timeline whose play-head sweeps across day markers, lighting each event
 * node and card as it passes. One-off animation (IntersectionObserver +
 * requestAnimationFrame), so it lives with the /app page.
 */

const STATS = [
  {
    label: translate({
      id: 'pages.index.weekTimeline.stats.actions.label',
      message: 'Bot actions',
      description: 'Week timeline stat label',
    }),
    value: '412',
    accent: false,
    sub: translate({
      id: 'pages.index.weekTimeline.stats.actions.sub',
      message: 'this week',
      description: 'Week timeline stat sub',
    }),
  },
  {
    label: translate({
      id: 'pages.index.weekTimeline.stats.opened.label',
      message: 'You opened the app',
      description: 'Week timeline stat label',
    }),
    value: '2×',
    accent: true,
    sub: translate({
      id: 'pages.index.weekTimeline.stats.opened.sub',
      message: 'Mon · Sun',
      description: 'Week timeline stat sub',
    }),
  },
  {
    label: translate({
      id: 'pages.index.weekTimeline.stats.time.label',
      message: 'Your time spent',
      description: 'Week timeline stat label',
    }),
    value: '90s',
    accent: true,
    sub: translate({
      id: 'pages.index.weekTimeline.stats.time.sub',
      message: 'vs. 4–6 hrs manual',
      description: 'Week timeline stat sub',
    }),
  },
];

const DAYS = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN'];

type EventColor = 'turq' | 'pos' | 'warn' | 'frost';

const EVENTS: {
  color: EventColor;
  left: number;
  icon: string;
  when: string;
  title: string;
  tag: string;
}[] = [
  {
    color: 'turq',
    left: 7,
    icon: '€',
    when: 'Mon · 08:14',
    title: translate({
      id: 'pages.index.weekTimeline.events.dca.title',
      message: 'Payday DCA fires.',
      description: 'Week timeline event title',
    }),
    tag: translate({
      id: 'pages.index.weekTimeline.events.dca.tag',
      message: '€200 deployed',
      description: 'Week timeline event tag',
    }),
  },
  {
    color: 'pos',
    left: 36,
    icon: '↘',
    when: 'Wed · 14:22',
    title: translate({
      id: 'pages.index.weekTimeline.events.grid.title',
      message: 'Grid catches SOL dip.',
      description: 'Week timeline event title',
    }),
    tag: '+€42.18',
  },
  {
    color: 'warn',
    left: 64,
    icon: '⏸',
    when: 'Fri · 19:48',
    title: translate({
      id: 'pages.index.weekTimeline.events.risk.title',
      message: 'Risk rule auto-pauses.',
      description: 'Week timeline event title',
    }),
    tag: translate({
      id: 'pages.index.weekTimeline.events.risk.tag',
      message: 'protected',
      description: 'Week timeline event tag',
    }),
  },
  {
    color: 'frost',
    left: 93,
    icon: '✓',
    when: 'Sun · 11:02',
    title: translate({
      id: 'pages.index.weekTimeline.events.glance.title',
      message: 'You glance, 90s.',
      description: 'Week timeline event title',
    }),
    tag: translate({
      id: 'pages.index.weekTimeline.events.glance.tag',
      message: '+€186.40 / wk',
      description: 'Week timeline event tag',
    }),
  },
];

const LOOP_MS = 9000;

export default function WeekTimeline(): ReactNode {
  const rootRef = useRef<HTMLDivElement>(null);
  const playRef = useRef<HTMLSpanElement>(null);
  const nodeRefs = useRef<(HTMLSpanElement | null)[]>([]);
  const cardRefs = useRef<(HTMLDivElement | null)[]>([]);

  useEffect(() => {
    const root = rootRef.current;
    const play = playRef.current;
    if (!root || !play) {
      return undefined;
    }

    let raf = 0;
    let start = 0;
    let running = false;

    const loop = (now: number) => {
      if (!start) {
        start = now;
      }
      const pct = (((now - start) % LOOP_MS) / LOOP_MS) * 100;
      play.style.left = `${pct}%`;
      EVENTS.forEach((event, i) => {
        const node = nodeRefs.current[i];
        const card = cardRefs.current[i];
        if (
          node &&
          card &&
          Math.abs(pct - event.left) < 1.5 &&
          !node.classList.contains(styles.nodeHot)
        ) {
          node.classList.add(styles.nodeHot);
          card.classList.add(styles.cardHot);
          window.setTimeout(() => node.classList.remove(styles.nodeHot), 1200);
          window.setTimeout(() => card.classList.remove(styles.cardHot), 1400);
        }
      });
      raf = window.requestAnimationFrame(loop);
    };

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting && !running) {
            running = true;
            raf = window.requestAnimationFrame(loop);
          }
        });
      },
      {threshold: 0.25},
    );
    observer.observe(root);

    return () => {
      observer.disconnect();
      window.cancelAnimationFrame(raf);
    };
  }, []);

  return (
    <GlassCard variant="strong" padded={false} className={styles.wrap}>
      <div className={styles.stats}>
        {STATS.map((stat) => (
          <div key={stat.label} className={styles.stat}>
            <div className={styles.statLabel}>{stat.label}</div>
            <div className={styles.statValue}>
              {stat.accent ? (
                <span className={styles.statAccent}>{stat.value}</span>
              ) : (
                stat.value
              )}
            </div>
            <div className={styles.statSub}>{stat.sub}</div>
          </div>
        ))}
      </div>

      <div className={styles.timeline} ref={rootRef}>
        <div className={styles.rail} />
        <div className={styles.days}>
          {DAYS.map((day) => (
            <div key={day} className={styles.dayCol}>
              <span className={styles.dayLab}>{day}</span>
              <span className={styles.tick} />
            </div>
          ))}
        </div>
        {EVENTS.map((event, i) => (
          <span
            key={event.title}
            ref={(el) => {
              nodeRefs.current[i] = el;
            }}
            className={styles.node}
            data-color={event.color}
            style={{left: `${event.left}%`}}
          />
        ))}
        <span className={styles.you} style={{left: '7%'}}>
          <Translate
            id="pages.index.weekTimeline.you"
            description="Week timeline 'you' marker">
            you
          </Translate>
        </span>
        <span className={styles.you} style={{left: '93%'}}>
          <Translate
            id="pages.index.weekTimeline.you"
            description="Week timeline 'you' marker">
            you
          </Translate>
        </span>
        <span className={styles.play} ref={playRef} style={{left: '0%'}} />
      </div>

      <div className={styles.cards}>
        {EVENTS.map((event, i) => (
          <div
            key={event.title}
            ref={(el) => {
              cardRefs.current[i] = el;
            }}
            className={styles.card}
            data-color={event.color}>
            <div className={styles.cardIcon}>{event.icon}</div>
            <div className={styles.cardWhen}>{event.when}</div>
            <h4 className={styles.cardTitle}>{event.title}</h4>
            <span className={styles.cardTag}>{event.tag}</span>
          </div>
        ))}
      </div>
    </GlassCard>
  );
}
