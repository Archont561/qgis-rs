import { defineCollection } from 'astro:content';
import { docsSchema } from '@astrojs/starlight/schema';

// Without this the `docs` collection has no schema, so Starlight's frontmatter
// defaults (notably `draft: false`) are never applied. Production builds filter
// on `data.draft === false` and would therefore emit zero pages.
export const collections = {
  docs: defineCollection({ schema: docsSchema() }),
};
