# @qgis-sdk/bridge

Typed QWebChannel bridge for QGIS plugins — auto-injects `qrc:///qtwebchannel/qwebchannel.js`, provides Promise API, React/Vue/Web Components adapters, with auto-generated TypeScript types from Python bridge classes.

## Features

- **Auto-injects** `qrc:///qtwebchannel/qwebchannel.js` with fallbacks (`./qwebchannel.js`, CDN)
- **Promisifies** callback-style Python `@pyqtSlot(..., result=...)` to `Promise`
- **Typed** — generate TS interfaces from Python bridge via CLI
- **Framework adapters**: vanilla JS, React hook, Vue composable, Web Components element
- **Python → JS messages** via `CustomEvent('qgis-message')`

## Install

```bash
npm install @qgis-sdk/bridge
# or
pnpm add @qgis-sdk/bridge
# or
bun add @qgis-sdk/bridge
```

## Python side (QGIS plugin)

```python
from PyQt5.QtCore import QObject, pyqtSlot, QVariant

class Bridge(QObject):
    @pyqtSlot(result=QVariant)
    def get_layer(self):
        return {"name": "roads", "count": 100}

    @pyqtSlot(str, result=QVariant)
    def log(self, msg: str):
        print(msg)
        return f"logged: {msg}"
```

Register in your plugin:

```python
from PyQt5.QtWebChannel import QWebChannel
channel = QWebChannel()
bridge = Bridge()
channel.registerObject("bridge", bridge)
web_view.page().setWebChannel(channel)
```

## Generate TypeScript types

```bash
qgis-plugin bridge generate --bridge my_plugin.bridge:Bridge --output web/bridge.d.ts
# or generate full package
qgis-plugin bridge generate --bridge my_plugin.bridge:Bridge --output web/ --package
```

This inspects your Python class signatures + type hints and emits:

```typescript
export interface Bridge {
  get_layer(): Promise<{ name: string; count: number }>;
  log(msg: string): Promise<string>;
}
```

## Usage — Vanilla JS / TypeScript

```typescript
import { createBridge } from '@qgis-sdk/bridge';
import type { Bridge } from './web/bridge.d.ts';

const bridge = await createBridge<Bridge>();
const layer = await bridge.get_layer();
await bridge.log("hello from JS");

// Listen for messages from Python
window.addEventListener('qgis-message', (e: CustomEvent) => {
  console.log('from Python:', e.detail);
});
```

Python → JS:

```python
web_view.page().runJavaScript("window.qgisBridge.onMessage({message: 'hi'})")
# or
web_view.page().runJavaScript(f"window.dispatchEvent(new CustomEvent('qgis-message', {{detail: {json.dumps(data)}}}}))")
```

## Usage — React

```tsx
import { useQgisBridge } from '@qgis-sdk/bridge/react';
import type { Bridge } from './web/bridge.d.ts';

function App() {
  const { bridge, ready, error } = useQgisBridge<Bridge>();

  if (!ready) return <div>Connecting to QGIS...</div>;
  if (error) return <div>Error: {error.message}</div>;

  return (
    <button onClick={() => bridge?.log("hello")}>
      Send to Python
    </button>
  );
}
```

## Usage — Vue

```vue
<script setup lang="ts">
import { useQgisBridge } from '@qgis-sdk/bridge/vue';
import type { Bridge } from './web/bridge.d.ts';

const { bridge, ready } = useQgisBridge<Bridge>();
</script>

<template>
  <div v-if="ready">
    <button @click="bridge?.value?.log('hello')">Send</button>
  </div>
</template>
```

## Usage — Web Components

```html
<qgis-bridge object-name="bridge" id="qgisBridge"></qgis-bridge>
<script type="module">
  import '@qgis-sdk/bridge/webcomponents';
  const el = document.getElementById('qgisBridge');
  el.addEventListener('qgis-bridge-ready', async (e) => {
    const layer = await e.detail.bridge.get_layer();
    console.log(layer);
  });
  el.addEventListener('qgis-message', (e) => {
    console.log('from Python', e.detail);
  });
</script>
```

Or as mixin:

```typescript
import { withQgisBridge } from '@qgis-sdk/bridge/webcomponents';

class MyMap extends withQgisBridge(HTMLElement) {
  onBridgeReady(bridge) {
    bridge.get_layer().then(layer => this.render(layer));
  }
  onQgisMessage(data) {
    console.log('from Python', data);
  }
}
customElements.define('my-map', MyMap);
```

## API

### `createBridge<T>(objectName?, options?)`

- `objectName` (default `'bridge'`) — name registered in Python via `channel.registerObject`
- `options.qwebchannelSources` — custom sources for qwebchannel.js loader
- `options.timeout` — ms before rejecting (default 10000)

Returns `Promise<T>` with promisified methods.

### `loadQWebChannel(sources?)`

Loads `qwebchannel.js` from first available source. Sources tried in order:
1. Already loaded global `QWebChannel`
2. `qrc:///qtwebchannel/qwebchannel.js` (Qt built-in)
3. `./qwebchannel.js` (local bundle)
4. CDN fallback

### `onQgisMessage(handler)`

Register handler for messages from Python. Returns unsubscribe function.

## qrc:///qtwebchannel/qwebchannel.js

Qt provides `qwebchannel.js` at `qrc:///qtwebchannel/qwebchannel.js` — no need to bundle it yourself. This package auto-injects it. For offline dev, you can also bundle:

```bash
# Find qwebchannel.js in your Qt installation
find /usr -name qwebchannel.js 2>/dev/null
# Copy to your web/ dir
cp /usr/share/qt5/.../qwebchannel.js ./web/
```

## License

GPL-2.0-or-later — same as QGIS
