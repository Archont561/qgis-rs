# AGENTS.md — machine instructions for this bundle

This is an **offline pixi sandbox**, not source code to merge.

- authoritative manifest: `.pixi-sandbox/manifest.json` (schema 1);
- environments: dev, docs (platform linux-64);
- root bootstrap: `./pixi-sandbox` (or `restore.sh` / `restore.ps1`); the verified manifest copy remains under `.pixi-sandbox/tools/linux-64/pixi-sandbox`;
- never download tools at restore time; bundled tools are: pixi, pixi-sandbox, pixi-unpack;
- after restore, `.pixi/tools/linux-64/pixi` install --frozen --offline must be a no-op.
