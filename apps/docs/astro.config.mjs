import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';

// https://astro.build/config
export default defineConfig({
  server: {
    allowedHosts: 'all',
  },
  integrations: [
    starlight({
      title: 'qgis-rs',
      description: 'Rust bindings for QGIS — render QGIS projects at native speed',
      logo: {
        src: './src/assets/logo.svg',
      },
      social: {
        github: 'https://github.com/yourusername/qgis-rs',
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
