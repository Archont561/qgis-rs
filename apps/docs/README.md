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

## Structure

```
apps/docs/
├── src/
│   ├── assets/           # Images, logos
│   ├── content/
│   │   └── docs/         # Markdown/MDX documentation pages
│   │       ├── getting-started/
│   │       ├── concepts/
│   │       ├── guides/
│   │       ├── reference/
│   │       ├── cli/
│   │       └── server/
│   └── styles/           # Custom CSS
├── public/               # Static assets
├── astro.config.mjs      # Astro configuration
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

Build the site:

```bash
npm run build
```

The output is in `dist/`. Deploy to any static hosting service:

- **Netlify**: Drag & drop `dist/` folder
- **Vercel**: `vercel --prod`
- **GitHub Pages**: Upload `dist/` to `gh-pages` branch
- **Cloudflare Pages**: Connect repo, build command `npm run build`, output `dist/`

## Technologies

- [Astro](https://astro.build/) — Static site generator
- [Starlight](https://starlight.astro.build/) — Documentation theme
- [TypeScript](https://www.typescriptlang.org/) — Type safety
- [MDX](https://mdxjs.com/) — Markdown + JSX
