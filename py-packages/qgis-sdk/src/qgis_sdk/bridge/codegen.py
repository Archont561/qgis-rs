"""
qgis_sdk.bridge — TypeScript bridge generation from Python bridge classes.

Generates typed TS definitions from Python bridge classes decorated with @pyqtSlot
or plain methods, for use with @qgis-sdk/bridge npm package.

The generated TS provides:
- Typed interface for bridge methods (callback + Promise overloads)
- Auto-injection of qrc:///qtwebchannel/qwebchannel.js
- Framework adapters (React hook, Vue composable, Web Components)

Usage:

    from qgis_sdk.bridge import generate_ts_bridge, generate_js_wrapper, generate_package
    from my_plugin.dialogs.web_dialog import Bridge

    # Generate .d.ts
    ts_code = generate_ts_bridge(Bridge, name="Bridge")
    Path("web/bridge.d.ts").write_text(ts_code)

    # Generate JS wrapper with auto-injection
    js_code = generate_js_wrapper(Bridge, name="Bridge")
    Path("web/bridge.js").write_text(js_code)

    # Generate full npm package files (for @qgis-sdk/bridge)
    generate_package(Bridge, output_dir="frontend/src/qgis-bridge", name="Bridge")

CLI:

    qgis-plugin bridge generate --bridge my_plugin.dialogs.web_dialog:Bridge --output web/bridge.ts --framework react
"""

from __future__ import annotations

import inspect
import json
import textwrap
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Type, get_type_hints


# ── Python type -> TS type mapping ──────────────────────────────────────────

PY_TO_TS: Dict[str, str] = {
    "str": "string",
    "int": "number",
    "float": "number",
    "bool": "boolean",
    "dict": "Record<string, any>",
    "Dict": "Record<string, any>",
    "list": "any[]",
    "List": "any[]",
    "tuple": "any[]",
    "Tuple": "any[]",
    "Any": "any",
    "None": "void",
    "NoneType": "void",
}

def _py_type_to_ts(py_type: Any) -> str:
    """Map Python type annotation to TS type string."""
    if py_type is None:
        return "void"
    # Handle string annotations
    if isinstance(py_type, str):
        return PY_TO_TS.get(py_type, py_type)

    # Handle actual types
    type_name = getattr(py_type, "__name__", str(py_type))
    
    # Handle Optional / Union
    origin = getattr(py_type, "__origin__", None)
    args = getattr(py_type, "__args__", None)
    
    # Optional[X] is Union[X, None]
    if origin is not None and args:
        # Check if it's Union
        if "Union" in str(origin) or "UnionType" in str(type(py_type)):
            # Filter out None
            non_none = [a for a in args if a is not type(None) and getattr(a, "__name__", "") != "NoneType"]
            if len(non_none) == 1:
                return f"{_py_type_to_ts(non_none[0])} | null"
            else:
                return " | ".join(_py_type_to_ts(a) for a in non_none)
        # List[X], Dict[K,V], etc
        if origin in (list, List) or type_name == "list":
            if args:
                inner = _py_type_to_ts(args[0])
                return f"{inner}[]"
            return "any[]"
        if origin in (dict, Dict) or type_name == "dict":
            return "Record<string, any>"

    # Direct mapping
    if type_name in PY_TO_TS:
        return PY_TO_TS[type_name]
    
    # For complex types, try to infer from name
    if "Dict" in type_name or "dict" in type_name:
        return "Record<string, any>"
    if "List" in type_name or "list" in type_name:
        return "any[]"
    
    # Default: use type name as-is, but lowercase first char if needed
    # For custom classes, use any
    return "any"


def _extract_methods(bridge_cls: Type) -> List[Tuple[str, inspect.Signature, Dict[str, Any], Any]]:
    """Extract public methods from bridge class with signatures and type hints."""
    methods = []
    # Try to get type hints for the class
    try:
        hints = get_type_hints(bridge_cls)
    except Exception:
        hints = {}

    for name in dir(bridge_cls):
        if name.startswith("_"):
            continue
        attr = getattr(bridge_cls, name)
        if not callable(attr):
            continue
        # Skip if it's a class or module
        if inspect.isclass(attr):
            continue
        try:
            sig = inspect.signature(attr)
        except (ValueError, TypeError):
            continue

        # Get method-specific hints
        try:
            method_hints = get_type_hints(attr)
        except Exception:
            method_hints = {}

        # Return annotation
        return_hint = method_hints.get("return", hints.get(name, None))

        methods.append((name, sig, method_hints, return_hint))

    return methods


def generate_ts_bridge(bridge_cls: Type, name: str = "Bridge", with_promise: bool = True, with_callback: bool = True) -> str:
    """
    Generate TypeScript interface from Python bridge class.

    Example output:

        export interface Bridge {
          get_layer(callback: (result: string) => void): void;
          get_layer(): Promise<string>;
          log(message: string, callback: (result: string) => void): void;
          log(message: string): Promise<string>;
        }

    Args:
        bridge_cls: Python class with bridge methods
        name: TS interface name
        with_promise: Generate Promise overloads
        with_callback: Generate callback overloads (QWebChannel style)
    """
    methods = _extract_methods(bridge_cls)

    lines = [
        "/**",
        f" * Auto-generated from Python {bridge_cls.__module__}.{bridge_cls.__name__}",
        " * Generated by qgis_sdk.bridge.generate_ts_bridge",
        " * Do not edit manually — regenerate via: qgis-plugin bridge generate",
        " */",
        "",
        f"export interface {name} {{",
    ]

    for method_name, sig, hints, return_hint in methods:
        params = list(sig.parameters.values())
        # Filter out self/cls
        params = [p for p in params if p.name not in ("self", "cls")]

        ts_return = _py_type_to_ts(return_hint) if return_hint else "any"
        # QWebChannel returns string (JSON) or QVariant, but we map to any for flexibility
        # If return is dict/list, it comes as stringified JSON in callback style, but as object in Promise style via our wrapper
        # So we generate: callback result is string, promise result is ts_return or string

        # Build param list for TS
        ts_params = []
        for p in params:
            param_type = hints.get(p.name, None)
            ts_type = _py_type_to_ts(param_type) if param_type else "any"
            # If param has default, make optional
            optional = "?" if p.default != inspect.Parameter.empty else ""
            ts_params.append(f"{p.name}{optional}: {ts_type}")

        # Callback overload: last param is callback
        if with_callback:
            callback_params = ts_params + [f"callback: (result: {ts_return if ts_return != 'void' else 'string'}) => void"]
            lines.append(f"  {method_name}({', '.join(callback_params)}): void;")

        # Promise overload
        if with_promise:
            # Promise returns ts_return, but if ts_return is void, return string (raw)
            promise_return = ts_return if ts_return != "void" else "string"
            # For methods that return dict/list, promise returns the typed object, not string
            # Our JS wrapper JSON.parse's if result is stringified JSON
            lines.append(f"  {method_name}({', '.join(ts_params)}): Promise<{promise_return}>;")

        # If neither, generate simple signature
        if not with_callback and not with_promise:
            lines.append(f"  {method_name}({', '.join(ts_params)}): {ts_return};")

    lines.append("}")
    lines.append("")
    lines.append(f"export type {name}Callback = {name};")
    lines.append("")
    lines.append("// Utility type for bridge ready state")
    lines.append(f"export interface {name}State {{")
    lines.append(f"  bridge: {name} | null;")
    lines.append(f"  ready: boolean;")
    lines.append(f"}}")
    lines.append("")

    return "\n".join(lines)


def generate_js_wrapper(bridge_cls: Type, name: str = "Bridge", object_name: str = "bridge") -> str:
    """
    Generate JavaScript wrapper that auto-injects qwebchannel.js and provides Promise API.

    This is the runtime that @qgis-sdk/bridge provides — but this function generates
    a standalone version for inclusion without npm.

    The wrapper:
    - Auto-injects qrc:///qtwebchannel/qwebchannel.js if QWebChannel not present
    - Creates QWebChannel and returns typed bridge
    - Wraps callback-style to Promise-style
    """

    methods = _extract_methods(bridge_cls)
    method_names = [m[0] for m in methods]

    js_methods = ",\n  ".join(f'"{m}"' for m in method_names)

    return f"""/**
 * Auto-generated JS wrapper for {name}
 * From Python {bridge_cls.__module__}.{bridge_cls.__name__}
 * Generated by qgis_sdk.bridge.generate_js_wrapper
 * Includes auto-injection of qrc:///qtwebchannel/qwebchannel.js
 */

// Auto-inject qwebchannel.js if needed
function loadQWebChannel() {{
  return new Promise((resolve, reject) => {{
    if (typeof QWebChannel !== 'undefined') {{
      resolve();
      return;
    }}
    // Try Qt built-in
    const sources = [
      'qrc:///qtwebchannel/qwebchannel.js',
      './qwebchannel.js',
      'https://cdn.jsdelivr.net/npm/qwebchannel@6.1.0/qwebchannel.js'
    ];
    let idx = 0;
    function tryLoad() {{
      if (idx >= sources.length) {{
        reject(new Error('Failed to load qwebchannel.js from any source'));
        return;
      }}
      const script = document.createElement('script');
      script.src = sources[idx];
      script.onload = () => {{
        if (typeof QWebChannel !== 'undefined') resolve();
        else {{ idx++; tryLoad(); }}
      }};
      script.onerror = () => {{ idx++; tryLoad(); }};
      document.head.appendChild(script);
    }}
    tryLoad();
  }});
}}

function promisifyBridge(rawBridge) {{
  const wrapped = {{}};
  const methods = [{js_methods}];
  methods.forEach(methodName => {{
    if (typeof rawBridge[methodName] !== 'function') return;
    wrapped[methodName] = function(...args) {{
      const lastArg = args[args.length - 1];
      const hasCallback = typeof lastArg === 'function';
      
      if (hasCallback) {{
        // Callback style: bridge.method(arg, callback)
        return rawBridge[methodName].apply(rawBridge, args);
      }} else {{
        // Promise style: bridge.method(arg).then(...)
        return new Promise((resolve, reject) => {{
          try {{
            rawBridge[methodName].apply(rawBridge, [...args, (result) => {{
              // Try to JSON.parse if result is stringified JSON
              try {{
                const parsed = typeof result === 'string' ? JSON.parse(result) : result;
                // If parsed is object with error, reject
                if (parsed && typeof parsed === 'object' && parsed.error) {{
                  reject(new Error(parsed.error));
                }} else {{
                  resolve(parsed !== undefined ? parsed : result);
                }}
              }} catch(e) {{
                // Not JSON, return raw
                resolve(result);
              }}
            }}]);
          }} catch(e) {{
            reject(e);
          }}
        }});
      }}
    }});
  }});
  // Copy non-function properties
  Object.keys(rawBridge).forEach(k => {{
    if (typeof rawBridge[k] !== 'function' && !wrapped[k]) {{
      wrapped[k] = rawBridge[k];
    }}
  }});
  return wrapped;
}}

export function createBridge(objectName = '{object_name}') {{
  return loadQWebChannel().then(() => {{
    return new Promise((resolve, reject) => {{
      try {{
        new QWebChannel(qt.webChannelTransport, (channel) => {{
          const raw = channel.objects[objectName];
          if (!raw) {{
            reject(new Error(`Bridge object '${{objectName}}' not found in QWebChannel. Did you register it via channel.registerObject('{object_name}', bridge)?`));
            return;
          }}
          resolve(promisifyBridge(raw));
        }});
      }} catch(e) {{
        reject(e);
      }}
    }});
  }});
}}

// React hook (if React available)
export function useQgisBridge(objectName = '{object_name}') {{
  // This is a generic hook — actual React implementation is in @qgis-sdk/bridge/react
  // For standalone usage without React, use createBridge()
  if (typeof React === 'undefined') {{
    console.warn('React not found — use createBridge() instead of useQgisBridge()');
    return {{ bridge: null, ready: false }};
  }}
  const [bridge, setBridge] = React.useState(null);
  const [ready, setReady] = React.useState(false);
  React.useEffect(() => {{
    createBridge(objectName).then(b => {{ setBridge(b); setReady(true); }}).catch(console.error);
  }}, [objectName]);
  return {{ bridge, ready }};
}}

// Python → JS entry points — auto-dispatch to framework if present
window.qgisBridge = window.qgisBridge || {{}};
window.qgisBridge.createBridge = createBridge;
window.qgisBridge.loadQWebChannel = loadQWebChannel;

// Auto-dispatch CustomEvent for any framework to listen
window.updateFromPython = window.updateFromPython || function(data) {{
  console.log('[qgis-bridge] From Python:', data);
  window.dispatchEvent(new CustomEvent('qgis-message', {{ detail: data }}));
  window.dispatchEvent(new CustomEvent('qgis-bridge-message', {{ detail: data }}));
  if (window.qgisBridge.onMessage) window.qgisBridge.onMessage(data);
}};

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {{
  module.exports = {{ createBridge, loadQWebChannel, useQgisBridge }};
}}
"""


def generate_package(bridge_cls: Type, output_dir: str | Path, name: str = "Bridge", object_name: str = "bridge") -> Path:
    """
    Generate full package with TS types + JS wrapper + framework adapters.

    Creates:
        output_dir/
            bridge.d.ts      — TS interface
            bridge.js        — JS wrapper with auto-injection
            index.ts         — main entry (re-exports)
            react.ts         — React hook (typed)
            vue.ts           — Vue composable (typed)
            webcomponents.ts — Web Components helper
            README.md

    This can be copied into frontend/src/ or used as basis for @qgis-sdk/bridge.
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    # TS interface
    ts_code = generate_ts_bridge(bridge_cls, name=name)
    (out / "bridge.d.ts").write_text(ts_code, encoding="utf-8")

    # JS wrapper
    js_code = generate_js_wrapper(bridge_cls, name=name, object_name=object_name)
    (out / "bridge.js").write_text(js_code, encoding="utf-8")

    # index.ts — main entry that re-exports and provides typed createBridge
    index_ts = f"""/** @qgis-sdk/bridge — typed wrapper for QGIS QWebChannel bridge
 * Auto-generated from Python {bridge_cls.__module__}.{bridge_cls.__name__}
 */

import type {{ {name} }} from './bridge.d.ts';

export type {{ {name} }} from './bridge.d.ts';

export {{ createBridge, loadQWebChannel }} from './bridge.js';

export function createTypedBridge(objectName = '{object_name}'): Promise<{name}> {{
  // @ts-ignore — bridge.js is JS, but we cast to typed
  const {{ createBridge }} = require('./bridge.js');
  return createBridge(objectName) as Promise<{name}>;
}}

// Re-export framework adapters
export * from './react.js';
export * from './vue.js';
export * from './webcomponents.js';
"""
    (out / "index.ts").write_text(index_ts, encoding="utf-8")

    # react.ts
    react_ts = f"""import type {{ {name} }} from './bridge.d.ts';
import {{ createBridge }} from './bridge.js';

export interface {name}State {{
  bridge: {name} | null;
  ready: boolean;
}}

// Generic hook — works with React 18+ CDN or bundled
export function useQgisBridge(objectName = '{object_name}'): {name}State {{
  // @ts-ignore — React may be global or imported
  const ReactGlobal = (typeof React !== 'undefined' ? React : null) as any;
  if (!ReactGlobal) {{
    console.warn('[qgis-bridge] React not found — use createBridge() instead');
    return {{ bridge: null, ready: false }};
  }}
  const [bridge, setBridge] = ReactGlobal.useState(null);
  const [ready, setReady] = ReactGlobal.useState(false);
  ReactGlobal.useEffect(() => {{
    createBridge(objectName).then((b: {name}) => {{ setBridge(b); setReady(true); }}).catch(console.error);
  }}, [objectName]);
  return {{ bridge, ready }};
}}

// For bundlers: import {{ useState, useEffect }} from 'react'
export function createReactHook(React: any) {{
  return function useQgisBridgeTyped(objectName = '{object_name}'): {name}State {{
    const [bridge, setBridge] = React.useState<{name} | null>(null);
    const [ready, setReady] = React.useState(false);
    React.useEffect(() => {{
      // @ts-ignore
      import('./bridge.js').then(({{ createBridge }}) => {{
        createBridge(objectName).then((b: {name}) => {{ setBridge(b); setReady(true); }});
      }});
    }}, [objectName]);
    return {{ bridge, ready }};
  }};
}}
"""
    (out / "react.ts").write_text(react_ts, encoding="utf-8")

    # vue.ts
    vue_ts = f"""import type {{ {name} }} from './bridge.d.ts';
import {{ createBridge }} from './bridge.js';

export function useQgisBridge(objectName = '{object_name}') {{
  // @ts-ignore — Vue may be global or imported
  const VueGlobal = (typeof Vue !== 'undefined' ? Vue : null) as any;
  if (!VueGlobal) {{
    console.warn('[qgis-bridge] Vue not found — use createBridge()');
    return {{ bridge: null, ready: false, layer: null }};
  }}
  const bridge = VueGlobal.ref(null);
  const ready = VueGlobal.ref(false);
  const layer = VueGlobal.ref(null);

  VueGlobal.onMounted(() => {{
    createBridge(objectName).then((b: {name}) => {{
      bridge.value = b;
      ready.value = true;
    }});
  }});

  return {{ bridge, ready, layer }};
}}

export function createVueComposable(Vue: any) {{
  return function useQgisBridgeTyped(objectName = '{object_name}') {{
    const bridge = Vue.ref<{name} | null>(null);
    const ready = Vue.ref(false);
    Vue.onMounted(() => {{
      createBridge(objectName).then((b: {name}) => {{
        bridge.value = b;
        ready.value = true;
      }});
    }});
    return {{ bridge, ready }};
  }};
}}
"""
    (out / "vue.ts").write_text(vue_ts, encoding="utf-8")

    # webcomponents.ts
    wc_ts = f"""import type {{ {name} }} from './bridge.d.ts';
import {{ createBridge }} from './bridge.js';

export class QgisBridgeElement extends HTMLElement {{
  bridge: {name} | null = null;
  ready = false;

  connectedCallback() {{
    createBridge().then(b => {{
      this.bridge = b as {name};
      this.ready = true;
      this.dispatchEvent(new CustomEvent('bridge-ready', {{ detail: b }}));
    }});
  }}

  call<K extends keyof {name}>(method: K, ...args: any[]): Promise<any> {{
    if (!this.bridge) return Promise.reject('Bridge not ready');
    // @ts-ignore
    return (this.bridge[method] as any)(...args);
  }}
}}

if (typeof customElements !== 'undefined' && !customElements.get('qgis-bridge')) {{
  customElements.define('qgis-bridge', QgisBridgeElement);
}}

export function defineQgisComponents() {{
  if (typeof customElements === 'undefined') return;
  if (!customElements.get('qgis-bridge')) {{
    customElements.define('qgis-bridge', QgisBridgeElement);
  }}
}}
"""
    (out / "webcomponents.ts").write_text(wc_ts, encoding="utf-8")

    # README
    readme = f"""# {name} Bridge — @qgis-sdk/bridge

Auto-generated from Python `{bridge_cls.__module__}.{bridge_cls.__name__}` via `qgis_sdk.bridge`.

## Usage

### Vanilla JS

```html
<script src="qrc:///qtwebchannel/qwebchannel.js"></script>
<script type="module">
import {{ createBridge }} from './bridge.js';
const bridge = await createBridge(); // auto-injects qwebchannel.js if needed
const layer = await bridge.get_layer();
console.log(layer);
</script>
```

### React

```tsx
import {{ useQgisBridge }} from './react.js'; // or from '@qgis-sdk/bridge/react'
function App() {{
  const {{ bridge, ready }} = useQgisBridge();
  useEffect(() => {{
    if (ready) bridge.get_layer().then(setLayer);
  }}, [ready]);
}}
```

### Vue

```vue
<script setup>
import {{ useQgisBridge }} from './vue.js';
const {{ bridge, ready }} = useQgisBridge();
</script>
```

### Web Components

```html
<qgis-bridge id="qgisBridge"></qgis-bridge>
<script type="module">
import {{ defineQgisComponents }} from './webcomponents.js';
defineQgisComponents();
document.getElementById('qgisBridge').addEventListener('bridge-ready', e => {{
  e.detail.get_layer().then(console.log);
}});
</script>
```

## Python → JS

```python
dlg.run_js("updateFromPython({{message: 'hi'}})")
# JS listens via CustomEvent('qgis-message')
window.addEventListener('qgis-message', e => console.log(e.detail));
```

## Regenerate

```bash
qgis-plugin bridge generate --bridge my_plugin.dialogs.web_dialog:Bridge --output web/ --framework react
# or
python -c "from qgis_sdk.bridge import generate_package; from my_plugin.dialogs.web_dialog import Bridge; generate_package(Bridge, 'web/bridge', 'Bridge')"
```
"""
    (out / "README.md").write_text(readme, encoding="utf-8")

    return out


def load_bridge_class(dotted_path: str) -> Type:
    """
    Load bridge class from dotted path like 'my_plugin.dialogs.web_dialog:Bridge' or 'my_plugin.dialogs.web_dialog.Bridge'.

    Supports both colon and dot notation for class.
    """
    if ":" in dotted_path:
        module_path, class_name = dotted_path.split(":", 1)
    else:
        # Split last dot as class
        if "." not in dotted_path:
            raise ValueError(f"Invalid dotted path: {dotted_path} — expected 'module:Class' or 'module.Class'")
        module_path, class_name = dotted_path.rsplit(".", 1)

    import importlib
    mod = importlib.import_module(module_path)
    cls = getattr(mod, class_name)
    if not isinstance(cls, type):
        # If it's an instance, get its class
        cls = type(cls)
    return cls


__all__ = [
    "generate_ts_bridge",
    "generate_js_wrapper",
    "generate_package",
    "load_bridge_class",
]
