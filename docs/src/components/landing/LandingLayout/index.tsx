import React, {type ReactNode} from 'react';
import Head from '@docusaurus/Head';
import LandingNav, {type LandingNavLink} from '../LandingNav';
import LandingFooter from '../LandingFooter';
import styles from './styles.module.css';

interface LandingLayoutProps {
  /** Document <title>. The site title is appended automatically. */
  title: string;
  /** Meta description for SEO / social cards. */
  description?: string;
  children: ReactNode;
  /** Override the default landing nav links. */
  navLinks?: LandingNavLink[];
  /** Hide the custom landing nav entirely (for bare splash pages). */
  noNav?: boolean;
  /** Hide the landing footer. */
  noFooter?: boolean;
  /** Halo intensity for the page background. */
  halo?: 'full' | 'subtle' | 'none';
}

/**
 * Standalone page shell for marketing landing / feature pages.
 *
 * Deliberately does NOT use `@theme/Layout` — Docusaurus renders any
 * `src/pages` component that skips the theme Layout without the docs navbar
 * or footer (the documented "standalone page" pattern). This keeps full
 * creative control while still getting routing, SSR and the global theme CSS.
 */
export default function LandingLayout({
  title,
  description,
  children,
  navLinks,
  noNav,
  noFooter,
  halo = 'full',
}: LandingLayoutProps): ReactNode {
  const haloClass =
    halo === 'full' ? 'bg-halo' : halo === 'subtle' ? 'bg-halo-subtle' : '';

  return (
    <>
      <Head>
        <html lang="en" className={styles.html} />
        <title>{title}</title>
        {description && <meta name="description" content={description} />}
        {description && <meta property="og:description" content={description} />}
        <meta property="og:title" content={title} />
      </Head>
      <div className={`${styles.root} ${haloClass}`}>
        {!noNav && <LandingNav links={navLinks} />}
        <main className={styles.main}>{children}</main>
        {!noFooter && <LandingFooter />}
      </div>
    </>
  );
}
