# Proposed GitHub repo description & topics

> **Note:** `gh repo edit` returns 403 for `arena-ai-coding-agent[bot]` — no admin. Owner needs to set via GitHub UI or with a PAT that has admin.

## Description (160 chars, fits GitHub limit)

```
Safe, idiomatic Rust bindings for QGIS — render maps, tiles, WMS/WFS server, plus Python & TypeScript APIs and QGIS plugin SDK with Qt dialogs, WebEngine HTML (React/Vue/Web Components + QWebChannel) and Rust acceleration
```

Shorter fallback (if GitHub truncates):

```
Rust bindings for QGIS — map rendering, tiles, server, Python/TS APIs, plugin SDK with UI + WebEngine + Rust
```

## Homepage

```
https://archont561.github.io/qgis-rs/
```

## Topics (20 max, GitHub allows)

```
qgis
rust
gis
geospatial
pyqgis
qgis-plugin
map-rendering
wms
wfs
xyz-tiles
python
typescript
qgis-server
cargo
pixi
webengine
qwebchannel
react
vue
web-components
```

Suggested order for discoverability: `qgis`, `rust`, `gis`, `geospatial`, `pyqgis`, `qgis-plugin`, `map-rendering`, `python`, `typescript`, `qgis-server`, `wms`, `wfs`, `react`, `vue`.

## How to set (owner)

Via UI: Repo → ⚙️ Settings → General → Description / Website / Topics → Save

Via CLI (with admin PAT):

```bash
gh repo edit Archont561/qgis-rs \
  --description "Safe, idiomatic Rust bindings for QGIS — render maps, tiles, WMS/WFS server, plus Python & TypeScript APIs and QGIS plugin SDK with Qt dialogs, WebEngine HTML (React/Vue/Web Components + QWebChannel) and Rust acceleration" \
  --homepage "https://archont561.github.io/qgis-rs/" \
  --add-topic qgis --add-topic rust --add-topic gis --add-topic geospatial --add-topic pyqgis --add-topic qgis-plugin --add-topic map-rendering --add-topic wms --add-topic wfs --add-topic xyz-tiles --add-topic python --add-topic typescript --add-topic qgis-server --add-topic cargo --add-topic pixi --add-topic webengine --add-topic qwebchannel --add-topic react --add-topic vue --add-topic web-components
```

Or via API:

```bash
curl -X PATCH -H "Authorization: token $GH_TOKEN" -H "Accept: application/vnd.github.v3+json" \
  https://api.github.com/repos/Archont561/qgis-rs \
  -d '{"description":"Safe, idiomatic Rust bindings for QGIS — render maps, tiles, WMS/WFS server, plus Python & TypeScript APIs and QGIS plugin SDK with Qt dialogs, WebEngine HTML (React/Vue/Web Components + QWebChannel) and Rust acceleration","homepage":"https://archont561.github.io/qgis-rs/"}'

curl -X PUT -H "Authorization: token $GH_TOKEN" -H "Accept: application/vnd.github.mercy-preview+json" \
  https://api.github.com/repos/Archont561/qgis-rs/topics \
  -d '{"names":["qgis","rust","gis","geospatial","pyqgis","qgis-plugin","map-rendering","wms","wfs","xyz-tiles","python","typescript","qgis-server","cargo","pixi","webengine","qwebchannel","react","vue","web-components"]}'
```
