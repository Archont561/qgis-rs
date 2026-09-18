/** qgis-sdk-bridge window.ts — QgisBridge extends EventTarget, windows-like (EventSource/WebSocket) */

import type { BridgeDescription } from './description';
import { loadDescription } from './description';

export interface BridgeOptions {
  objectName?: string;
  qwebchannelSources?: string[];
  timeout?: number;
  enableQgisApi?: boolean;
  qgisObjectName?: string;
}

export class QgisBridge extends EventTarget {
  // Like WebSocket readyState
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;

  readyState: number = QgisBridge.CONNECTING;
  url: string = 'qgis://bridge';
  description: BridgeDescription | null = null;

  // Properties like window / WebSocket / EventSource
  onopen: ((ev: Event) => void) | null = null;
  onmessage: ((ev: MessageEvent) => void) | null = null;
  onerror: ((ev: Event) => void) | null = null;
  onclose: ((ev: CloseEvent) => void) | null = null;

  // Dynamic bridge methods
  [method: string]: any;

  private _objectName: string;
  private _options: BridgeOptions;
  private _rawBridge: any = null;
  private _rawQgis: any = null;
  private _channel: any = null;

  constructor(objectName = 'bridge', options: BridgeOptions = {}) {
    super();
    this._objectName = objectName;
    this._options = options;
    this.url = `qgis://${objectName}`;
  }

  get objectName() {
    return this._objectName;
  }

  get rawBridge() {
    return this._rawBridge;
  }

  get rawQgis() {
    return this._rawQgis;
  }

  async _connect(): Promise<void> {
    const { loadQWebChannel } = await import('./loader.js');
    
    // Try to load description from window first (injected by Python)
    this.description = loadDescription();
    
    await loadQWebChannel(this._options.qwebchannelSources);

    return new Promise((resolve, reject) => {
      const timeout = this._options.timeout || 10000;
      let timeoutId: any;

      if (timeout > 0) {
        timeoutId = setTimeout(() => {
          this.readyState = QgisBridge.CLOSED;
          const err = new Error(`QWebChannel bridge '${this._objectName}' timeout after ${timeout}ms`);
          this.dispatchEvent(new CustomEvent('error', { detail: err }));
          if (this.onerror) this.onerror(new Event('error'));
          reject(err);
        }, timeout);
      }

      try {
        const QWebChannelGlobal = (typeof window !== 'undefined' ? (window as any).QWebChannel : null) || (typeof (globalThis as any).QWebChannel !== 'undefined' ? (globalThis as any).QWebChannel : null);
        
        if (!QWebChannelGlobal) {
          clearTimeout(timeoutId);
          const err = new Error('QWebChannel not available after loading qwebchannel.js');
          this.readyState = QgisBridge.CLOSED;
          this.dispatchEvent(new CustomEvent('error', { detail: err }));
          reject(err);
          return;
        }

        const transport = (typeof window !== 'undefined' ? (window as any).qt?.webChannelTransport : null) || (typeof (globalThis as any).qt !== 'undefined' ? (globalThis as any).qt?.webChannelTransport : null);

        if (!transport) {
          if (typeof process !== 'undefined' && (process as any).env?.NODE_ENV === 'test') {
            clearTimeout(timeoutId);
            this.readyState = QgisBridge.OPEN;
            this._setupProxy();
            this.dispatchEvent(new Event('open'));
            if (this.onopen) this.onopen(new Event('open'));
            resolve();
            return;
          }
          // If no transport but description available (e.g., testing without QGIS), still open
          if (this.description) {
            clearTimeout(timeoutId);
            this.readyState = QgisBridge.OPEN;
            this._setupProxy();
            this.dispatchEvent(new Event('open'));
            if (this.onopen) this.onopen(new Event('open'));
            resolve();
            return;
          }
          clearTimeout(timeoutId);
          const err = new Error('qt.webChannelTransport not available — are you running inside QWebEngineView?');
          this.readyState = QgisBridge.CLOSED;
          this.dispatchEvent(new CustomEvent('error', { detail: err }));
          reject(err);
          return;
        }

        new QWebChannelGlobal(transport, (channel: any) => {
          clearTimeout(timeoutId);
          this._channel = channel;
          const raw = channel.objects[this._objectName];
          const rawQgis = channel.objects[this._options.qgisObjectName || 'qgis'];

          if (!raw && !this.description) {
            const err = new Error(`Bridge object '${this._objectName}' not found. Available: ${Object.keys(channel.objects).join(', ')}`);
            this.readyState = QgisBridge.CLOSED;
            this.dispatchEvent(new CustomEvent('error', { detail: err }));
            reject(err);
            return;
          }

          this._rawBridge = raw || {};
          this._rawQgis = rawQgis || null;

          // Load description if not already loaded, or use injected
          if (!this.description) {
            this.description = loadDescription();
          }

          this.readyState = QgisBridge.OPEN;
          this._setupProxy();
          
          this.dispatchEvent(new Event('open'));
          if (this.onopen) this.onopen(new Event('open'));
          
          resolve();
        });
      } catch (e) {
        clearTimeout(timeoutId);
        this.readyState = QgisBridge.CLOSED;
        const err = e as Error;
        this.dispatchEvent(new CustomEvent('error', { detail: err }));
        if (this.onerror) this.onerror(new Event('error'));
        reject(e);
      }
    });
  }

  private _setupProxy() {
    // Create proxy for direct method access: bridge.get_layer() -> call()
    if (!this._rawBridge) return;

    const methodNames = Object.keys(this._rawBridge).filter(k => typeof this._rawBridge[k] === 'function');
    
    methodNames.forEach(methodName => {
      if (this[methodName]) return; // Don't overwrite existing
      this[methodName] = (...args: any[]) => this.call(methodName, ...args);
    });

    // If description available, also add methods from description that may not be in raw yet
    if (this.description) {
      this.description.methods.forEach(m => {
        if (!this[m.name]) {
          this[m.name] = (...args: any[]) => this.call(m.name, ...args);
        }
      });
    }
  }

  async _getRawQgis(): Promise<any> {
    return this._rawQgis;
  }

  // WebSocket-like
  send(data: any): void {
    if (this._rawBridge && typeof this._rawBridge.send === 'function') {
      this._rawBridge.send(data);
      return;
    }
    const ev = new MessageEvent('message', { data });
    this.dispatchEvent(ev);
    if (this.onmessage) this.onmessage(ev);
  }

  close(code?: number, reason?: string): void {
    this.readyState = QgisBridge.CLOSING;
    this.readyState = QgisBridge.CLOSED;
    const ev = new CloseEvent('close', { code: code || 1000, reason: reason || '' });
    this.dispatchEvent(ev);
    if (this.onclose) this.onclose(ev);
  }

  // EventSource-like — already inherits addEventListener/removeEventListener from EventTarget
  // But we provide typed overloads
  addEventListener(type: string, listener: EventListenerOrEventListenerObject | null, options?: boolean | AddEventListenerOptions): void {
    super.addEventListener(type, listener as any, options);
    // Also wire up on* properties
    if (type === 'open' && typeof listener === 'function') {
      // For onopen, we don't auto-set, but we can track
    }
  }

  removeEventListener(type: string, listener: EventListenerOrEventListenerObject | null, options?: boolean | EventListenerOptions): void {
    super.removeEventListener(type, listener as any, options);
  }

  // Window-like
  postMessage(message: any, targetOrigin?: string): void {
    this.send(message);
  }

  // Bridge method call — like fetch but for bridge
  async call<T>(method: string, ...args: any[]): Promise<T> {
    if (!this._rawBridge) {
      // If no raw bridge but in test mode, return mock
      if (this.readyState === QgisBridge.OPEN) {
        console.warn(`[QgisBridge] No raw bridge, returning mock for ${method}`);
        return null as T;
      }
      throw new Error(`Bridge not connected (readyState=${this.readyState})`);
    }

    const rawMethod = this._rawBridge[method];
    if (typeof rawMethod !== 'function') {
      throw new Error(`Method ${method} not found on bridge '${this._objectName}'. Available: ${Object.keys(this._rawBridge).filter(k => typeof this._rawBridge[k] === 'function').join(', ')}`);
    }

    return new Promise<T>((resolve, reject) => {
      try {
        const lastArg = args[args.length - 1];
        const hasCallback = typeof lastArg === 'function';
        if (hasCallback) {
          rawMethod.apply(this._rawBridge, args);
        } else {
          rawMethod.apply(this._rawBridge, [
            ...args,
            (result: any) => {
              try {
                if (typeof result === 'string') {
                  try {
                    const parsed = JSON.parse(result);
                    resolve(parsed as T);
                    return;
                  } catch {
                    // Not JSON
                  }
                }
                resolve(result as T);
              } catch (e) {
                reject(e);
              }
            }
          ]);
        }
      } catch (e) {
        reject(e);
      }
    });
  }

  // Convenience for dispatching from Python
  dispatchEvent(event: Event): boolean {
    const result = super.dispatchEvent(event);
    // Also call on* handlers
    if (event.type === 'open' && this.onopen) {
      this.onopen(event);
    } else if (event.type === 'message' && this.onmessage) {
      this.onmessage(event as MessageEvent);
    } else if (event.type === 'error' && this.onerror) {
      this.onerror(event);
    } else if (event.type === 'close' && this.onclose) {
      this.onclose(event as CloseEvent);
    }
    return result;
  }
}

// Factory — like new EventSource(url) or new WebSocket(url)
export async function createBridge<T = QgisBridge>(
  objectName: string | BridgeOptions = 'bridge',
  options: BridgeOptions = {}
): Promise<T & QgisBridge> {
  const opts: BridgeOptions = typeof objectName === 'string' ? { objectName, ...options } : objectName;
  const name = opts.objectName || (typeof objectName === 'string' ? objectName : 'bridge');
  
  const win = new QgisBridge(name, opts) as T & QgisBridge;
  await win._connect();
  return win;
}
