import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';

import remarkBaseLinks from './remark-base-links.mjs';

// Deployed to GitHub Pages as a project site, so the site lives under the
// /qgis-rs subpath: https://archont561.github.io/qgis-rs/
// See .github/workflows/pages.yml for the deployment.
const site = 'https://archont561.github.io';
const base = '/qgis-rs';

// https://astro.build/config
export default defineConfig({
  site,
  base,
  server: {
    allowedHosts: 'all',
  },
  // Content links such as `[Quick Start](/getting-started/quick-start)` are
  // emitted verbatim by the markdown pipeline, so prefix them with `base`.
  markdown: {
    remarkPlugins: [remarkBaseLinks(base)],
  },
  integrations: [
    starlight({
      title: 'qgis-rs',
      description: 'Rust bindings for QGIS — render QGIS projects at native speed',
      logo: {
        src: './src/assets/logo.svg',
      },
      social: {
        github: 'https://github.com/Archont561/qgis-rs',
      },
      editLink: {
        baseUrl: 'https://github.com/Archont561/qgis-rs/edit/main/apps/docs/',
      },
      sidebar: [
        {
          label: 'Getting Started',
          items: [
            { label: 'Introduction', link: '/getting-started/introduction' },
            { label: 'Installation', link: '/getting-started/installation' },
            { label: 'Quick Start', link: '/getting-started/quick-start' },
          ],
        },
        {
          label: 'Core Concepts',
          items: [
            { label: 'Architecture', link: '/concepts/architecture' },
            { label: 'API Design', link: '/concepts/api-design' },
            { label: 'QGIS Integration', link: '/concepts/qgis-integration' },
          ],
        },
        {
          label: 'API Reference',
          autogenerate: { directory: 'reference' },
        },
        {
          label: 'Guides',
          items: [
            { label: 'Rendering Projects', link: '/guides/rendering-projects' },
            { label: 'Working with Layers', link: '/guides/working-with-layers' },
            { label: 'Plugin Development', link: '/guides/plugin-development' },
            { label: 'Typed QWebChannel Bridge', link: '/guides/typed-bridge' },
            { label: 'Web Frameworks in QGIS', link: '/guides/web-frameworks' },
            { label: 'Testing Fixtures', link: '/guides/testing-fixtures' },
            { label: 'Network & Tasks', link: '/guides/network-tasks' },
          ],
        },
        {
          label: 'CLI',
          autogenerate: { directory: 'cli' },
        },
        {
          label: 'Server',
          autogenerate: { directory: 'server' },
        },
      ],
      customCss: ['./src/styles/custom.css'],
    }),
  ],
});
