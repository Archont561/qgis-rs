# @qgis-sdk/bridge

Typed [QWebChannel](https://doc.qt.io/qt-6/qtwebchannel-javascript.html) bridge
for QGIS plugins: the JavaScript half of a plugin whose UI runs in a
`QgsWebView`/`QWebEngineView` and whose logic runs in Python.

- **No codegen.** The Python side publishes a `BridgeDescription` (method
  names, arities, docs); this package builds the typed proxy from it at
  runtime, so adding a slot in Python needs no build step here.
- **Window-like.** `QgisBridge` extends `EventTarget` and mirrors the
  `WebSocket` surface you already know — `readyState`, `onopen`, `onmessage`,
  `send()`, `close()` — instead of inventing a transport vocabulary.
- **A complete QGIS API**, not just a channel: `qgis.layers`, `qgis.project`,
  `qgis.message`, `qgis.tasks`, `qgis.network`, `qgis.iface`, `qgis.settings`,
  `qgis.processing`.
- **Framework adapters** as separate entry points, so importing the bridge
  never pulls React, Vue or Svelte into a plugin that uses none of them.

## Installation

```bash
bun add @qgis-sdk/bridge     # npm install / pnpm add / yarn add all work
```

The Python counterpart is the `qgis-sdk` distribution in this repository; it is
what serves the description this package loads.

## Usage

```typescript
import { createQgisBridge } from "@qgis-sdk/bridge";

const { bridge, qgis } = await createQgisBridge();

await qgis.message.info("Hello", "from the web view");
const layer = await qgis.layers.addVector("/data/roads.shp", "Roads");
const task = await qgis.tasks.run("buffer_task", { distance: 10 });
const response = await qgis.network.fetch("https://example.com/api");

bridge.addEventListener("message", (event) => console.log(event.data));
```

A plugin that exposes its own slots and wants nothing else:

```typescript
import { createBridge } from "@qgis-sdk/bridge";

const bridge = await createBridge();
const features = await bridge.get_layer("my_layer");
```

### Entry points

| Import | What it gives you |
| --- | --- |
| `@qgis-sdk/bridge` | `createQgisBridge`, `createBridge`, `QgisBridge`, the sub-APIs, the description helpers |
| `@qgis-sdk/bridge/react` | `useQgisBridge`, `useQgis`, `useQgisMessage` |
| `@qgis-sdk/bridge/vue` | composables with the same shape |
| `@qgis-sdk/bridge/svelte` | stores with the same shape |
| `@qgis-sdk/bridge/webcomponents` | a custom element wrapper |
| `@qgis-sdk/bridge/loader` | `loadQWebChannel`, `isQWebChannelAvailable` — `qwebchannel.js` discovery |
| `@qgis-sdk/bridge/description` | `loadDescription`, `createBridgeFromDescription`, `descriptionToTypeScript` |
| `@qgis-sdk/bridge/qgis` | the `QgisAPI` class and its result types |
| `@qgis-sdk/bridge/window` | `QgisBridge` and `BridgeOptions` alone |

## Development

From the repository root — every verb below is a package script, fanned out by
turbo, so it behaves the same here and in CI:

```bash
bun x turbo run build      --filter=@qgis-sdk/bridge
bun x turbo run test       --filter=@qgis-sdk/bridge
bun x turbo run typecheck  --filter=@qgis-sdk/bridge
bun x turbo run lint       --filter=@qgis-sdk/bridge
bun x turbo run pack:check --filter=@qgis-sdk/bridge   # the published tarball still has what `files` promises
```

The full repository gate is `pixi run ci` (see the root `README.md`).

## License

GPL-2.0-or-later, like QGIS itself.
