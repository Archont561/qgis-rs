# Offline sandbox (orphan branch)

Built 2026-09-24T12:26:59Z from commit `84ee9a7` for platform `linux-64`.
`pixi.lock` sha256 `b782b062888b5c2c663bc204e0218c24ed6ce0a6a7843a6833aca79824d02eab`.

The branch root includes `pixi-sandbox`; it is a convenience copy of the verified self-bootstrap binary. The manifest copy remains under `.pixi-sandbox/tools/linux-64/pixi-sandbox` for compatibility with older launchers.

| env | platform | packed | unpacked | files |
| --- | --- | ---: | ---: | ---: |
| `dev` | linux-64 | 1002.2 MiB | 4361.4 MiB | 376 |
| `docs` | linux-64 | 47.0 MiB | 171.3 MiB | 34 |

Cargo dependencies: **139 crates**, 80.5 MiB (loose) from `Cargo.lock` sha256 `100cf061d7ee…`; restore materialises them to `.pixi-sandbox/vendor/`. Built with cargo 1.98.1 (797e8a9bc 2026-08-05); rustc 1.98.1 (48a229cea 2026-09-01).

## Restore on the disconnected machine

```bash
./pixi-sandbox doctor --branch-location . --verify
./pixi-sandbox restore --branch-location . --output-path <project> --force
# or: ./restore.sh <project>
# then, with no network:
.pixi/tools/linux-64/pixi install --frozen --offline
source .pixi/sandbox-env.sh
```

Every manifest blob is verified before it is written into the working tree.
