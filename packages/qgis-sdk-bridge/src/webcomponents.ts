/**
 * Web Components adapter for QGIS bridge
 * 
 * Provides <qgis-bridge> custom element and mixin for typed bridge access
 * 
 * @example HTML
 * ```html
 * <qgis-bridge object-name="bridge" id="qgisBridge"></qgis-bridge>
 * <script type="module">
 *   import '@qgis-sdk/bridge/webcomponents';
 *   const el = document.getElementById('qgisBridge');
 *   el.addEventListener('qgis-bridge-ready', async (e) => {
 *     const layer = await e.detail.bridge.get_layer();
 *     console.log(layer);
 *   });
 * </script>
 * ```
 * 
 * @example JS Mixin
 * ```typescript
 * import { QgisBridgeElement, withQgisBridge } from '@qgis-sdk/bridge/webcomponents';
 * 
 * class MyMap extends withQgisBridge(HTMLElement) {
 *   onBridgeReady(bridge) {
 *     bridge.get_layer().then(layer => this.render(layer));
 *   }
 * }
 * customElements.define('my-map', MyMap);
 * ```
 */

import { createBridge, onQgisMessage, type BridgeOptions, type GenericBridge } from './index.js';

export interface QgisBridgeReadyEvent<T = GenericBridge> extends CustomEvent {
  detail: { bridge: T };
}

export interface QgisBridgeErrorEvent extends CustomEvent {
  detail: { error: Error };
}

export class QgisBridgeElement extends HTMLElement {
  static observedAttributes = ['object-name'];

  private _bridge: GenericBridge | null = null;
  private _ready = false;
  private _error: Error | null = null;
  private _objectName = 'bridge';

  get bridge(): GenericBridge | null { return this._bridge; }
  get ready(): boolean { return this._ready; }
  get error(): Error | null { return this._error; }
  get objectName(): string { return this._objectName; }

  constructor() {
    super();
  }

  attributeChangedCallback(name: string, _old: string | null, value: string | null) {
    if (name === 'object-name' && value) {
      this._objectName = value;
    }
  }

  connectedCallback() {
    this._objectName = this.getAttribute('object-name') || 'bridge';
    this._connect();
  }

  private _connect() {
    createBridge(this._objectName)
      .then(bridge => {
        this._bridge = bridge;
        this._ready = true;
        this.dispatchEvent(new CustomEvent('qgis-bridge-ready', {
          detail: { bridge },
          bubbles: true,
          composed: true,
        }));
        this.dispatchEvent(new CustomEvent('ready', {
          detail: { bridge },
          bubbles: true,
          composed: true,
        }));
      })
      .catch(err => {
        this._error = err as Error;
        this.dispatchEvent(new CustomEvent('qgis-bridge-error', {
          detail: { error: err },
          bubbles: true,
          composed: true,
        }));
        console.error('[qgis-bridge/wc] Failed to connect', err);
      });

    // Listen for messages from Python
    onQgisMessage((data) => {
      this.dispatchEvent(new CustomEvent('qgis-message', {
        detail: data,
        bubbles: true,
        composed: true,
      }));
    });
  }

  // Convenience: typed access
  getBridge<T extends GenericBridge = GenericBridge>(): T | null {
    return this._bridge as T | null;
  }
}

// Register custom element if in browser and not already defined
if (typeof window !== 'undefined' && typeof customElements !== 'undefined') {
  if (!customElements.get('qgis-bridge')) {
    customElements.define('qgis-bridge', QgisBridgeElement);
  }
}

// ── Mixin for extending any HTMLElement ─────────────────────────────────────

type Constructor<T = {}> = new (...args: any[]) => T;

export function withQgisBridge<TBase extends Constructor<HTMLElement>>(Base: TBase) {
  return class QgisBridgeMixin extends Base {
    _qgisBridge: GenericBridge | null = null;
    _qgisReady = false;
    _qgisError: Error | null = null;
    qgisObjectName = 'bridge';

    get qgisBridge(): GenericBridge | null { return this._qgisBridge; }
    get qgisReady(): boolean { return this._qgisReady; }

    connectedCallback() {
      // Call super if exists (for HTMLElement subclasses that override)
      const superProto = Object.getPrototypeOf(Object.getPrototypeOf(this));
      if (superProto && typeof superProto.connectedCallback === 'function') {
        superProto.connectedCallback.call(this);
      }

      createBridge(this.qgisObjectName)
        .then(bridge => {
          this._qgisBridge = bridge;
          this._qgisReady = true;
          this.dispatchEvent(new CustomEvent('qgis-bridge-ready', {
            detail: { bridge },
            bubbles: true,
            composed: true,
          }));
          if ((this as any).onBridgeReady) {
            (this as any).onBridgeReady(bridge);
          }
        })
        .catch(err => {
          this._qgisError = err as Error;
          if ((this as any).onBridgeError) {
            (this as any).onBridgeError(err);
          }
        });

      if ((this as any).onQgisMessage) {
        onQgisMessage((data) => {
          (this as any).onQgisMessage(data);
        });
      }
    }

    // To be overridden by subclass
    onBridgeReady?(bridge: GenericBridge): void;
    onBridgeError?(error: Error): void;
    onQgisMessage?(data: any): void;
  };
}

export default QgisBridgeElement;
