import React, {type ReactNode} from 'react';
import GlassCard from '@site/src/components/GlassCard';
import styles from './_CodeCard.module.css';

/*
 * Page-local deployment snippet — a static, syntax-highlighted values.yaml in
 * a mac-window frame. Bespoke presentation, kept with the /whitelabel page.
 */

const K = ({children}: {children: ReactNode}) => (
  <span className={styles.key}>{children}</span>
);
const S = ({children}: {children: ReactNode}) => (
  <span className={styles.str}>{children}</span>
);
const C = ({children}: {children: ReactNode}) => (
  <span className={styles.comment}>{children}</span>
);
const N = ({children}: {children: ReactNode}) => (
  <span className={styles.num}>{children}</span>
);

export default function CodeCard(): ReactNode {
  return (
    <GlassCard variant="strong" padded={false} className={styles.card}>
      <div className={styles.head}>
        <span className={styles.dot} />
        <span className={styles.dot} />
        <span className={styles.dot} />
        <span className={styles.name}>values.yaml</span>
        <span className={styles.meta}>octobot-wl · helm v3</span>
      </div>
      <pre className={styles.body}>
        <C># Your cluster. Your namespace. Your brand.</C>
        {'\n'}
        <K>brand</K>:{'\n'}
        {'  '}
        <K>name</K>: <S>&quot;Lyra Wealth&quot;</S>
        {'\n'}
        {'  '}
        <K>theme</K>: <S>&quot;./brand/lyra-tokens.json&quot;</S>
        {'\n'}
        {'  '}
        <K>domain</K>: <S>&quot;trade.lyrawealth.com&quot;</S>
        {'\n\n'}
        <K>engine</K>:{'\n'}
        {'  '}
        <K>replicas</K>: <N>3</N>
        {'\n'}
        {'  '}
        <K>storage</K>: <S>&quot;postgres://internal.lyra/octobot&quot;</S>
        {'\n'}
        {'  '}
        <K>strategies</K>: <S>&quot;git@lyra/quant-strategies.git&quot;</S>{' '}
        <C># bring your own</C>
        {'\n\n'}
        <K>frontend</K>:{'\n'}
        {'  '}
        <K>mode</K>: <S>&quot;full-app&quot;</S> <C># or &quot;widget&quot; | &quot;mobile&quot;</C>
        {'\n'}
        {'  '}
        <K>auth</K>: <S>&quot;oidc://sso.lyrawealth.com&quot;</S>
        {'\n\n'}
        <K>venues</K>:{'\n'}
        {'  - '}
        <K>id</K>: <S>&quot;lyra-binance&quot;</S> <K>keysFrom</K>:{' '}
        <S>&quot;vault://lyra/binance&quot;</S>
        {'\n'}
        {'  - '}
        <K>id</K>: <S>&quot;lyra-ib&quot;</S> <K>keysFrom</K>:{' '}
        <S>&quot;vault://lyra/ib&quot;</S>
        {'\n\n'}
        <C>
          # Deploy: helm install lyra-octo ./octobot-wl -f values.yaml
          {'\n'}# Nothing phones home. Updates are pulls, not pushes.
        </C>
      </pre>
    </GlassCard>
  );
}
