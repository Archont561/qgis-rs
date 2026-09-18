/**
 * Vue composables for QGIS bridge — with complete QGIS API, built with bun
 */

import { createBridge, createQgisBridge, onQgisMessage } from './index.js';
import type { QgisBridge, BridgeOptions } from './window.js';
import type { QgisAPI } from './qgis.js';

export function useQgisBridge(
  objectName: string | BridgeOptions = 'bridge',
  options: BridgeOptions = {}
) {
  let Vue: any;
  try {
    Vue = (typeof window !== 'undefined' ? (window as any).Vue : null);
  } catch {}

  if (!Vue) {
    console.warn('[qgis-bridge/vue] Vue not found globally — use createBridge() directly');
    return { bridge: null, ready: false, error: new Error('Vue not found') };
  }

  const bridge = Vue.ref(null);
  const ready = Vue.ref(false);
  const error = Vue.ref(null);

  Vue.onMounted(() => {
    const opts: BridgeOptions = typeof objectName === 'string' ? { objectName, ...options } : objectName;
    (createBridge as any)(opts)
      .then((b: any) => {
        bridge.value = b;
        ready.value = true;
      })
      .catch((err: any) => {
        error.value = err;
        console.error('[qgis-bridge/vue] Failed', err);
      });
  });

  return { bridge, ready, error };
}

export function useQgis(
  objectName: string | BridgeOptions = 'bridge',
  options: BridgeOptions = {}
) {
  let Vue: any;
  try {
    Vue = (typeof window !== 'undefined' ? (window as any).Vue : null);
  } catch {}

  if (!Vue) {
    console.warn('[qgis-bridge/vue] Vue not found for useQgis');
    return { bridge: null, qgis: null, ready: false, error: new Error('Vue not found') };
  }

  const bridge = Vue.ref(null);
  const qgis = Vue.ref(null);
  const ready = Vue.ref(false);
  const error = Vue.ref(null);

  Vue.onMounted(() => {
    const opts: BridgeOptions = typeof objectName === 'string' ? { objectName, ...options } : objectName;
    (createQgisBridge as any)(opts)
      .then((res: any) => {
        bridge.value = res.bridge;
        qgis.value = res.qgis;
        ready.value = true;
      })
      .catch((err: any) => {
        error.value = err;
        console.error('[qgis-bridge/vue] Failed', err);
      });
  });

  return { bridge, qgis, ready, error };
}

export function createVueComposable(Vue: any) {
  return function useQgisBridgeTyped(
    objectName: string | BridgeOptions = 'bridge',
    options: BridgeOptions = {}
  ) {
    const bridge = Vue.ref(null);
    const ready = Vue.ref(false);
    const error = Vue.ref(null);

    Vue.onMounted(() => {
      const opts: BridgeOptions = typeof objectName === 'string' ? { objectName, ...options } : objectName;
      (createBridge as any)(opts)
        .then((b: any) => {
          bridge.value = b;
          ready.value = true;
        })
        .catch((err: any) => error.value = err);
    });

    return { bridge, ready, error };
  };
}

export function createQgisVueComposable(Vue: any) {
  return function useQgisTyped(
    objectName: string | BridgeOptions = 'bridge',
    options: BridgeOptions = {}
  ) {
    const bridge = Vue.ref(null);
    const qgis = Vue.ref(null);
    const ready = Vue.ref(false);
    const error = Vue.ref(null);

    Vue.onMounted(() => {
      const opts: BridgeOptions = typeof objectName === 'string' ? { objectName, ...options } : objectName;
      (createQgisBridge as any)(opts)
        .then((res: any) => {
          bridge.value = res.bridge;
          qgis.value = res.qgis;
          ready.value = true;
        })
        .catch((err: any) => error.value = err);
    });

    return { bridge, qgis, ready, error };
  };
}

export function useQgisMessage<T = any>(handler: (data: T) => void) {
  let Vue: any;
  try {
    Vue = (typeof window !== 'undefined' ? (window as any).Vue : null);
  } catch {}
  
  if (!Vue) return;
  
  Vue.onMounted(() => {
    const off = onQgisMessage(handler);
    Vue.onUnmounted(off);
  });
}

export default useQgisBridge;
