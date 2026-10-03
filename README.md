# Offline sandbox (orphan branch)

Built 2026-10-03T17:02:48Z from commit `a4869d3` for platform `linux-64`.
`pixi.lock` sha256 `d07bb7bb295e61219c746b44462f08245679f906f7ce86f1939a0be06520fd68`.

The verified self-bootstrap binary is stored at `.pixi-sandbox/tools/linux-64/pixi-sandbox`. The branch root intentionally contains documentation only.

| env | platform | packed | unpacked | files |
| --- | --- | ---: | ---: | ---: |
| `bun` | linux-64 | 390.3 MiB | 1683.7 MiB | 45 |
| `default` | linux-64 | 1103.9 MiB | 4724.7 MiB | 401 |

Cargo dependencies: **139 crates**, 80.5 MiB (loose) from `Cargo.lock` sha256 `e2e4cbaeea39…`; restore materialises them to `.pixi-sandbox/vendor/`. Built with cargo 1.98.1 (797e8a9bc 2026-08-05); rustc 1.98.1 (48a229cea 2026-09-01).

## Restore on the disconnected machine

```bash
./.pixi-sandbox/tools/linux-64/pixi-sandbox doctor --branch-location . --verify
./.pixi-sandbox/tools/linux-64/pixi-sandbox restore --branch-location . --output-path <project> --force
# then, from <project> with no network, use pixi as the sole entrypoint:
pixi install --frozen --offline
pixi run --frozen -- cargo build --offline
```

Every manifest blob is verified before it is written into the working tree.
