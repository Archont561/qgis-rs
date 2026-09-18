# qgis-rs Documentation

Documentation site for qgis-rs, built with [Astro Starlight](https://starlight.astro.build/).

## Development

### Using Pixi (Recommended)

```bash
# Activate the docs environment
pixi shell -e docs

# Start dev server
pixi run docs-dev

# Build for production
pixi run docs-build

# Preview production build
pixi run docs-preview
```

### Using npm directly

```bash
# Install dependencies
npm install

# Start dev server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

### Lockfile

Dependencies are pinned by [`bun.lock`](./bun.lock); CI installs with
`bun install --frozen-lockfile`, so update it deliberately (`bun install`
locally, then commit) rather than letting CI float to the newest matching
versions. Note the `overrides`/`resolutions` entry for `@astrojs/sitemap` in
`package.json` — see the deployment notes below before removing it.

## Structure

```
apps/docs/
├── src/
│   ├── assets/           # Images, logos
│   ├── content/
│   │   ├── config.ts     # docs collection schema (Starlight frontmatter)
│   │   └── docs/         # Markdown/MDX documentation pages
│   │       ├── index.mdx # Landing page (site root)
│   │       ├── getting-started/
│   │       ├── concepts/
│   │       ├── guides/
│   │       ├── reference/
│   │       ├── cli/
│   │       └── server/
│   └── styles/           # Custom CSS
├── public/               # Static assets (favicon.svg, …)
├── astro.config.mjs      # Astro configuration (site, base, sidebar)
├── remark-base-links.mjs # Prefix in-content links with `base`
└── package.json
```

## Adding Documentation

Create `.md` or `.mdx` files in `src/content/docs/`:

```markdown
---
title: My Page
description: Page description for SEO
---

# My Page

Content here...
```

The sidebar is configured in `astro.config.mjs`.

## Deployment

The site is published to **GitHub Pages** at
<https://archont561.github.io/qgis-rs/> by
[`.github/workflows/pages.yml`](../../.github/workflows/pages.yml), which runs on
every push to `main` that touches `apps/docs/`, `pixi.toml`, or `pixi.lock`
(and on demand via *Actions → Pages → Run workflow*).

Because it is a *project* site it is served from the `/qgis-rs` subpath, so
`astro.config.mjs` sets:

```js
const site = 'https://archont561.github.io';
const base = '/qgis-rs';
```

Two consequences worth knowing:

- Root-absolute links in content (`[Quick Start](/getting-started/quick-start)`)
  are prefixed with `base` at build time by
  [`remark-base-links.mjs`](./remark-base-links.mjs). Add new links the same
  way — do not hardcode `/qgis-rs/…`.
- `base` also applies to `astro dev`, so the dev server listens on
  `http://localhost:4321/qgis-rs`.

### One-time repository setup

GitHub Pages must be switched to the Actions source once by a repository admin:
*Settings → Pages → Build and deployment → Source: **GitHub Actions***.
Until then the `deploy` job fails with *"Get Pages site failed"*.

### Building locally

```bash
npm run build     # output in dist/
npm run preview   # serve dist/ at http://localhost:4321/qgis-rs
```

The output in `dist/` is plain static files, so it can equally be uploaded to
Netlify, Vercel, or Cloudflare Pages — just keep `site`/`base` in
`astro.config.mjs` in sync with wherever it is hosted.

## Technologies

- [Astro](https://astro.build/) — Static site generator
- [Starlight](https://starlight.astro.build/) — Documentation theme
- [TypeScript](https://www.typescriptlang.org/) — Type safety
- [MDX](https://mdxjs.com/) — Markdown + JSX
