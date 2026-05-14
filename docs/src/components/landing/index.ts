/**
 * Landing-page toolkit — navbar-less, fully custom marketing pages.
 *
 * Build a page under `src/pages/` by composing these inside `LandingLayout`
 * (which skips the Docusaurus theme Layout, so no docs navbar/footer).
 * All components consume the Neo Glass Dark tokens from theme-tokens.css.
 */
export {default as LandingLayout} from './LandingLayout';
export {default as LandingNav} from './LandingNav';
export type {LandingNavLink} from './LandingNav';
export {default as LandingFooter} from './LandingFooter';
export {default as Hero} from './Hero';
export {default as Section} from './Section';
export {default as FeatureGrid} from './FeatureGrid';
export type {Feature} from './FeatureGrid';
export {default as CTABand} from './CTABand';
