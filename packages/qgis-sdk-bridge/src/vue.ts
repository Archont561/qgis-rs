/**
 * Vue composable for QGIS bridge — typed, auto-injects qwebchannel.js
 * 
 * @example
 * ```vue
 * <script setup lang="ts">
 * import { useQgisBridge } from '@qgis-sdk/bridge/vue';
 * import type { Bridge } from './web/bridge.d.ts';
 * 
 * const { bridge, ready, error } = useQgisBridge<Bridge>();
 * 
 * watch(ready, async (isReady) => {
 *   if (isReady && bridge.value) {
 *     const layer = await bridge.value.get_layer();
 *     console.log(layer);
 *   }
 * });
 * </script>
 * 
 * <template>
 *   <div v-if="!ready">Connecting to QGIS...</div>
 *   <div v-else-if="error">Error: {{ error.message }}</div>
 *   <div v-else>
 *     <button @click="bridge?.log('hello')">Send to Python</button>
 *   </div>
 * </template>
 * ```
 */

import { createBridge, onQgisMessage, type BridgeOptions, type GenericBridge } from './index.js';

export interface VueBridgeState<T> {
  bridge: { value: T | null };
  ready: { value: boolean };
  error: { value: Error | null };
}

interface VueReactivity {
  ref: <T>(value: T) => { value: T };
  onMounted: (fn: () => void) => void;
  watch?: (source: any, cb: any) => void;
  onUnmounted?: (fn: () => void) => void;
}

/**
 * Vue composable — tries to use global Vue or falls back to shim
 */
export function useQgisBridge<T extends GenericBridge = GenericBridge>(
  objectName: string | BridgeOptions = 'bridge',
  options: BridgeOptions = {}
): { bridge: { value: T | null }, ready: { value: boolean }, error: { value: Error | null } } {
  let Vue: VueReactivity | null = null;
  
  try {
    Vue = (typeof window !== 'undefined' ? (window as any).Vue : null) as VueReactivity;
    if (!Vue?.ref) {
      // Try Vue 3 global
      const maybeVue = (window as any).Vue;
      if (maybeVue?.ref) Vue = maybeVue;
    }
  } catch {}

  // Minimal shim for non-Vue environments (tests, fallback)
  const refShim = <V>(v: V) => ({ value: v });
  const onMountedShim = (fn: () => void) => { try { fn(); } catch {} };

  const _ref = Vue?.ref || refShim;
  const _onMounted = Vue?.onMounted || onMountedShim;

  const bridge = _ref<T | null>(null as any);
  const ready = _ref(false);
  const error = _ref<Error | null>(null);

  _onMounted(() => {
    const opts: BridgeOptions = typeof objectName === 'string' ? { objectName, ...options } : objectName;
    
    createBridge<T>(opts)
      .then(b => {
        bridge.value = b;
        ready.value = true;
      })
      .catch(err => {
        console.error('[qgis-bridge/vue] Failed to create bridge', err);
        error.value = err as Error;
      });
  });

  return { bridge, ready, error };
}

/**
 * Create Vue composable factory for bundlers where Vue is imported
 * 
 * @example
 * ```typescript
 * import { ref, onMounted } from 'vue';
 * import { createVueComposable } from '@qgis-sdk/bridge/vue';
 * import type { Bridge } from './bridge';
 * 
 * const useQgisBridge = createVueComposable<Bridge>({ ref, onMounted });
 * ```
 */
export function createVueComposable<T extends GenericBridge = GenericBridge>(Vue: VueReactivity) {
  return function useQgisBridgeTyped(
    objectName: string | BridgeOptions = 'bridge',
    options: BridgeOptions = {}
  ) {
    const bridge = Vue.ref<T | null>(null);
    const ready = Vue.ref(false);
    const error = Vue.ref<Error | null>(null);

    Vue.onMounted(() => {
      const opts: BridgeOptions = typeof objectName === 'string' ? { objectName, ...options } : objectName;
      
      import('./index.js').then(({ createBridge }) => {
        createBridge<T>(opts)
          .then(b => {
            bridge.value = b;
            ready.value = true;
          })
          .catch(err => error.value = err as Error);
      });
    });

    return { bridge, ready, error };
  };
}

/**
 * Composable for listening to messages from Python
 */
export function useQgisMessage<T = any>(handler: (data: T) => void) {
  let Vue: VueReactivity | null = null;
  try {
    Vue = (typeof window !== 'undefined' ? (window as any).Vue : null) as VueReactivity;
  } catch {}

  const _onMounted = Vue?.onMounted || ((fn: () => void) => fn());
  const _onUnmounted = Vue?.onUnmounted || (() => {});

  let unsubscribe: (() => void) | null = null;

  _onMounted(() => {
    unsubscribe = onQgisMessage(handler);
  });

  if (_onUnmounted) {
    _onUnmounted(() => {
      if (unsubscribe) unsubscribe();
    });
  }

  return { unsubscribe: () => { if (unsubscribe) unsubscribe(); } };
}

export default useQgisBridge;
