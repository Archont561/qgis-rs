/**
 * remark plugin — prefix root-absolute links in documentation content with the
 * configured Astro `base`.
 *
 * Starlight rewrites the links it generates itself (sidebar, logo, "edit this
 * page"), but links written inside `.md`/`.mdx` content are emitted verbatim.
 * A link like `[Quick Start](/getting-started/quick-start)` therefore points at
 * `https://archont561.github.io/getting-started/quick-start` instead of
 * `https://archont561.github.io/qgis-rs/getting-started/quick-start`, i.e. a
 * 404 on GitHub Pages.
 *
 * Usage (apps/docs/astro.config.mjs):
 *
 *   markdown: { remarkPlugins: [remarkBaseLinks(base)] }
 *
 * @param {string} base Astro `base`, e.g. `/qgis-rs`.
 */
export default function remarkBaseLinks(base) {
  const prefix = base && base !== '/' ? base.replace(/\/+$/, '') : '';

  const visit = (node) => {
    const url = node.url;
    // Only touch root-absolute URLs: `/foo`, not `https://…`, `//cdn…`, `#anchor`,
    // `mailto:…` or already-prefixed `/qgis-rs/…`.
    if (
      typeof url === 'string' &&
      url.startsWith('/') &&
      !url.startsWith('//') &&
      url !== `${prefix}/` &&
      !url.startsWith(`${prefix}/`)
    ) {
      node.url = prefix + url;
    }
    for (const child of node.children ?? []) visit(child);
  };

  return () => (tree) => {
    if (prefix) visit(tree);
  };
}
