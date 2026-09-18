/**
 * @qgis-sdk/bridge — Typed QWebChannel bridge for QGIS plugins
 * 
 * Auto-injects qrc:///qtwebchannel/qwebchannel.js, provides Promise API,
 * and supports auto-generated TS types from Python bridge classes.
 * 
 * @example Vanilla JS
 * ```typescript
 * import { createBridge } from '@qgis-sdk/bridge';
 * interface MyBridge {
 *   get_layer(): Promise<{name: string, count: number}>;
 *   log(msg: string): Promise<string>;
 * }
 * const bridge = await createBridge<MyBridge>();
 * const layer = await bridge.get_layer();
 * ```
 * 
 * @example With auto-generated types
 * ```typescript
 * // Generated via: qgis-plugin bridge generate --bridge my_plugin:Bridge --output web/bridge.d.ts
 * import type { Bridge } from './web/bridge.d.ts';
 * import { createBridge } from '@qgis-sdk/bridge';
 * const bridge = await createBridge<Bridge>();
 * ```
 */

import { loadQWebChannel, isQWebChannelAvailable } from './loader.js';

export { loadQWebChannel, isQWebChannelAvailable, QWEBCHANNEL_SOURCES } from './loader.js';

declare global {
  interface Window {
    QWebChannel?: any;
    qt?: any;
  }
  var QWebChannel: any;
  var qt: any;
}

export type QWebChannelCallback<T = any> = (result: T) => void;

/**
 * Generic bridge type — any object with methods that are either:
 * - callback style: method(arg, callback) => void
 * - promise style (wrapped): method(arg) => Promise<T>
 */
export type GenericBridge = Record<string, (...args: any[]) => any>;

/**
 * Convert callback-style bridge methods to Promise-style
 */
function promisifyBridge<T extends GenericBridge>(rawBridge: GenericBridge): T {
  const wrapped: GenericBridge = {};
  const methodNames = Object.keys(rawBridge).filter(k => typeof rawBridge[k] === 'function');

  methodNames.forEach(methodName => {
    const original = rawBridge[methodName];
    
    wrapped[methodName] = function(...args: any[]) {
      const lastArg = args[args.length - 1];
      const hasCallback = typeof lastArg === 'function';

      if (hasCallback) {
        // Already callback style — pass through
        return original.apply(rawBridge, args);
      } else {
        // Promise style
        return new Promise((resolve, reject) => {
          try {
            original.apply(rawBridge, [
              ...args,
              (result: any) => {
                try {
                  // Try to parse JSON if result is stringified JSON
                  if (typeof result === 'string') {
                    try {
                      const parsed = JSON.parse(result);
                      if (parsed && typeof parsed === 'object' && 'error' in parsed) {
                        reject(new Error(parsed.error));
                        return;
                      }
                      resolve(parsed !== undefined ? parsed : result);
                      return;
                    } catch {
                      // Not JSON, return raw string
                      resolve(result);
                      return;
                    }
                  }
                  resolve(result);
                } catch (e) {
                  reject(e);
                }
              }
            ]);
          } catch (e) {
            reject(e);
          }
        });
      }
    };
  });

  // Copy non-function properties
  Object.keys(rawBridge).forEach(k => {
    if (typeof rawBridge[k] !== 'function' && !(k in wrapped)) {
      wrapped[k] = rawBridge[k];
    }
  });

  return wrapped as T;
}

export interface BridgeOptions {
  /** QWebChannel object name, default 'bridge' (must match Python channel.registerObject) */
  objectName?: string;
  /** Custom sources for qwebchannel.js loader */
  qwebchannelSources?: string[];
  /** Timeout for bridge ready, ms */
  timeout?: number;
}

export interface BridgeState<T> {
  bridge: T | null;
  ready: boolean;
  error: Error | null;
}

/**
 * Create a typed bridge to Python — auto-injects qwebchannel.js
 * 
 * @param objectName - Name registered in Python via channel.registerObject("bridge", obj)
 * @param options - Loader options
 * @returns Promise that resolves to typed bridge
 * 
 * @example
 * ```typescript
 * const bridge = await createBridge<MyBridge>();
 * const data = await bridge.get_layer();
 * ```
 */
export function createBridge<T extends GenericBridge = GenericBridge>(
  objectName: string | BridgeOptions = 'bridge',
  options: BridgeOptions = {}
): Promise<T> {
  const opts: BridgeOptions = typeof objectName === 'string' ? { objectName, ...options } : objectName;
  const name = opts.objectName || (typeof objectName === 'string' ? objectName : 'bridge');

  return loadQWebChannel(opts.qwebchannelSources).then(() => {
    return new Promise<T>((resolve, reject) => {
      const timeout = opts.timeout || 10000;
      let timeoutId: any;

      if (timeout > 0) {
        timeoutId = setTimeout(() => {
          reject(new Error(`QWebChannel bridge '${name}' timeout after ${timeout}ms. Is Python bridge registered via channel.registerObject('${name}', obj)?`));
        }, timeout);
      }

      try {
        // @ts-ignore — QWebChannel global from qwebchannel.js
        const QWebChannelGlobal = (typeof window !== 'undefined' ? (window as any).QWebChannel : null) || (typeof QWebChannel !== 'undefined' ? QWebChannel : null);
        
        if (!QWebChannelGlobal) {
          clearTimeout(timeoutId);
          reject(new Error('QWebChannel not available after loading qwebchannel.js'));
          return;
        }

        // qt.webChannelTransport is injected by QWebEngineView
        const transport = (typeof window !== 'undefined' ? (window as any).qt?.webChannelTransport : null) || (typeof qt !== 'undefined' ? qt.webChannelTransport : null);
        
        if (!transport) {
          // In tests or outside QWebEngine, mock
          if (typeof process !== 'undefined' && process.env.NODE_ENV === 'test') {
            clearTimeout(timeoutId);
            // Return mock bridge for tests
            resolve({} as T);
            return;
          }
          clearTimeout(timeoutId);
          reject(new Error('qt.webChannelTransport not available — are you running inside QWebEngineView?'));
          return;
        }

        new QWebChannelGlobal(transport, (channel: any) => {
          clearTimeout(timeoutId);
          const raw = channel.objects[name];
          if (!raw) {
            reject(new Error(`Bridge object '${name}' not found in QWebChannel. Available: ${Object.keys(channel.objects).join(', ')}. Did you call channel.registerObject('${name}', bridge) in Python?`));
            return;
          }
          resolve(promisifyBridge<T>(raw));
        });
      } catch (e) {
        clearTimeout(timeoutId);
        reject(e);
      }
    });
  });
}

/**
 * Create bridge with callback API preserved (for legacy code)
 */
export function createCallbackBridge<T extends GenericBridge = GenericBridge>(
  objectName: string = 'bridge',
  options: BridgeOptions = {}
): Promise<T> {
  return loadQWebChannel(options.qwebchannelSources).then(() => {
    return new Promise<T>((resolve, reject) => {
      try {
        const QWebChannelGlobal = (typeof window !== 'undefined' ? (window as any).QWebChannel : null) || (typeof QWebChannel !== 'undefined' ? QWebChannel : null);
        const transport = (typeof window !== 'undefined' ? (window as any).qt?.webChannelTransport : null) || (typeof qt !== 'undefined' ? qt.webChannelTransport : null);
        
        if (!QWebChannelGlobal || !transport) {
          reject(new Error('QWebChannel or transport not available'));
          return;
        }

        new QWebChannelGlobal(transport, (channel: any) => {
          const raw = channel.objects[objectName];
          if (!raw) {
            reject(new Error(`Bridge '${objectName}' not found`));
            return;
          }
          resolve(raw as T);
        });
      } catch (e) {
        reject(e);
      }
    });
  });
}

// ── Python → JS helpers ─────────────────────────────────────────────────────

export type QgisMessageHandler = (data: any) => void;

const messageHandlers = new Set<QgisMessageHandler>();

/**
 * Register handler for messages from Python via runJavaScript
 * Python calls: web_view.page().runJavaScript("window.qgisBridge.onMessage({message: 'hi'})")
 */
export function onQgisMessage(handler: QgisMessageHandler): () => void {
  messageHandlers.add(handler);
  return () => messageHandlers.delete(handler);
}

/**
 * Global entry points that Python can call via runJavaScript
 * These dispatch to all registered handlers + CustomEvent
 */
function setupGlobalHandlers() {
  if (typeof window === 'undefined') return;

  const w = window as any;
  w.qgisBridge = w.qgisBridge || {};
  w.qgisBridge.createBridge = createBridge;
  w.qgisBridge.loadQWebChannel = loadQWebChannel;
  w.qgisBridge.onMessage = (data: any) => {
    messageHandlers.forEach(h => {
      try { h(data); } catch (e) { console.error('[qgis-bridge] handler error', e); }
    });
    window.dispatchEvent(new CustomEvent('qgis-message', { detail: data }));
    window.dispatchEvent(new CustomEvent('qgis-bridge-message', { detail: data }));
  };

  // Legacy entry points
  w.updateFromPython = w.updateFromPython || w.qgisBridge.onMessage;
  w.updateFromReact = w.updateFromReact || w.qgisBridge.onMessage;
  w.updateFromVue = w.updateFromVue || w.qgisBridge.onMessage;
  w.updateFromWC = w.updateFromWC || w.qgisBridge.onMessage;
}

if (typeof window !== 'undefined') {
  setupGlobalHandlers();
}

export default createBridge;
