/**
 * Web Components for QGIS bridge — with complete QGIS API, built with bun
 */

import { createBridge, createQgisBridge } from './index.js';
import type { QgisBridge, BridgeOptions } from './window.js';
import type { QgisAPI } from './qgis.js';

export class QgisBridgeElement extends HTMLElement {
  bridge: QgisBridge | null = null;
  qgis: QgisAPI | null = null;
  ready = false;

  private _objectName: string = 'bridge';
  private _options: BridgeOptions = {};

  static get observedAttributes() {
    return ['object-name', 'qgis-object-name'];
  }

  attributeChangedCallback(name: string, oldValue: string, newValue: string) {
    if (name === 'object-name' && oldValue !== newValue) {
      this._objectName = newValue;
    }
  }

  connectedCallback() {
    const objectName = this.getAttribute('object-name') || this._objectName;
    
    // Try qgis first (complete API), fallback to bridge only
    const enableQgis = this.hasAttribute('enable-qgis') || true;
    
    if (enableQgis) {
      createQgisBridge(objectName, this._options).then(res => {
        this.bridge = res.bridge;
        this.qgis = res.qgis;
        this.ready = true;
        this.dispatchEvent(new CustomEvent('bridge-ready', { detail: res }));
        this.dispatchEvent(new CustomEvent('qgis-ready', { detail: res.qgis }));
        // Make available as properties
        (this as any).qgis = res.qgis;
      }).catch(e => {
        console.error('[qgis-bridge] webcomponent failed', e);
        this.dispatchEvent(new CustomEvent('bridge-error', { detail: e }));
      });
    } else {
      createBridge(objectName, this._options).then(b => {
        this.bridge = b;
        this.ready = true;
        this.dispatchEvent(new CustomEvent('bridge-ready', { detail: b }));
      }).catch(e => {
        console.error('[qgis-bridge] webcomponent failed', e);
        this.dispatchEvent(new CustomEvent('bridge-error', { detail: e }));
      });
    }
  }

  call<T>(method: string, ...args: any[]): Promise<T> {
    if (!this.bridge) return Promise.reject(new Error('Bridge not ready'));
    return (this.bridge as any).call(method, ...args);
  }

  // Convenience for qgis API
  get layers() {
    return this.qgis?.layers;
  }

  get project() {
    return this.qgis?.project;
  }

  get message() {
    return this.qgis?.message;
  }
}

export class QgisElement extends HTMLElement {
  qgis: QgisAPI | null = null;
  bridge: QgisBridge | null = null;
  ready = false;

  connectedCallback() {
    const objectName = this.getAttribute('object-name') || 'bridge';
    createQgisBridge(objectName).then(res => {
      this.qgis = res.qgis;
      this.bridge = res.bridge;
      this.ready = true;
      (this as any).qgis = res.qgis;
      (this as any).bridge = res.bridge;
      this.dispatchEvent(new CustomEvent('qgis-ready', { detail: res.qgis }));
      this.dispatchEvent(new CustomEvent('bridge-ready', { detail: res }));
    });
  }
}

export function defineQgisComponents() {
  if (typeof customElements === 'undefined') return;
  
  if (!customElements.get('qgis-bridge')) {
    customElements.define('qgis-bridge', QgisBridgeElement);
  }
  if (!customElements.get('qgis-element')) {
    customElements.define('qgis-element', QgisElement);
  }
  if (!customElements.get('qgis-qgis')) {
    customElements.define('qgis-qgis', QgisElement);
  }
}

if (typeof window !== 'undefined') {
  // Auto-define when loaded
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', defineQgisComponents);
  } else {
    defineQgisComponents();
  }
}

export default QgisBridgeElement;
