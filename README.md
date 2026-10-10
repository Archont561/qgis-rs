# Offline sandbox (orphan branch)

Built 2026-10-10T17:24:43Z from commit `1bb7791` for platform `linux-64`.
`pixi.lock` sha256 `d74f4ab32d9004818d05bda5e8e601023b91f6612b114b1530bdcbabca67352a`.

The verified self-bootstrap binary is stored at `.pixi-sandbox/tools/linux-64/pixi-sandbox`. The branch root intentionally contains documentation only.

| env | platform | packed | unpacked | files |
| --- | --- | ---: | ---: | ---: |
| `bun` | linux-64 | 390.3 MiB | 1683.7 MiB | 45 |
| `default` | linux-64 | 1105.9 MiB | 4733.2 MiB | 413 |

Cargo dependencies: **162 crates**, 104.8 MiB (loose) from `Cargo.lock` sha256 `9f67e258c625…`; restore materialises them to `.pixi-sandbox/vendor/`. Built with cargo 1.99.0 (5f94df478 2026-08-27); rustc 1.99.0 (b940084d7 2026-09-28).

## Restore on the disconnected machine

```bash
./.pixi-sandbox/tools/linux-64/pixi-sandbox doctor --branch-location . --verify
./.pixi-sandbox/tools/linux-64/pixi-sandbox restore --branch-location . --output-path <project> --force
# then, from <project> with no network, use pixi as the sole entrypoint:
pixi install --frozen --offline
pixi run --frozen -- cargo build --offline
```

Every manifest blob is verified before it is written into the working tree.
