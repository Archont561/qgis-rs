/**
 * Svelte stores for QGIS bridge — with complete QGIS API, built with bun
 */

import { createBridge, createQgisBridge } from './index.js';
import type { QgisBridge, BridgeOptions } from './window.js';
import type { QgisAPI } from './qgis.js';

// Minimal writable store implementation for when svelte/store not available
function createWritable<T>(initial: T) {
  let value = initial;
  const subscribers = new Set<(v: T) => void>();
  
  return {
    subscribe(run: (v: T) => void) {
      run(value);
      subscribers.add(run);
      return () => subscribers.delete(run);
    },
    set(v: T) {
      value = v;
      subscribers.forEach(s => s(value));
    },
    update(fn: (v: T) => T) {
      value = fn(value);
      subscribers.forEach(s => s(value));
    }
  };
}

export interface QgisStore<T = QgisBridge> {
  bridge: T & QgisBridge | null;
  qgis: QgisAPI | null;
  ready: boolean;
  error: Error | null;
}

export function createQgisStore<T = QgisBridge>(
  objectName: string | BridgeOptions = 'bridge',
  options: BridgeOptions = {}
) {
  const store = createWritable<QgisStore<T>>({
    bridge: null,
    qgis: null,
    ready: false,
    error: null
  });

  const opts: BridgeOptions = typeof objectName === 'string' ? { objectName, ...options } : objectName;

  (createQgisBridge as any)(opts)
    .then((res: any) => {
      store.set({
        bridge: res.bridge,
        qgis: res.qgis,
        ready: true,
        error: null
      });
    })
    .catch((err: any) => {
      store.set({
        bridge: null,
        qgis: null,
        ready: false,
        error: err as Error
      });
    });

  return {
    subscribe: store.subscribe,
    // For Svelte 5 runes compatibility
    get ready() {
      let current: QgisStore<T>;
      store.subscribe(v => current = v)();
      return current!.ready;
    }
  };
}

export function createBridgeStore<T = QgisBridge>(
  objectName: string | BridgeOptions = 'bridge',
  options: BridgeOptions = {}
) {
  const store = createWritable<{
    bridge: (T & QgisBridge) | null;
    ready: boolean;
    error: Error | null;
  }>({
    bridge: null,
    ready: false,
    error: null
  });

  const opts: BridgeOptions = typeof objectName === 'string' ? { objectName, ...options } : objectName;

  (createBridge as any)(opts)
    .then((b: any) => {
      store.set({ bridge: b, ready: true, error: null });
    })
    .catch((err: any) => {
      store.set({ bridge: null, ready: false, error: err as Error });
    });

  return {
    subscribe: store.subscribe
  };
}

// Default store for easy import
export const qgisStore = createQgisStore();
export const bridgeStore = createBridgeStore();

export default qgisStore;
