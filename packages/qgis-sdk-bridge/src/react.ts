/**
 * React hook for QGIS bridge — typed, auto-injects qwebchannel.js
 */

import { createBridge, onQgisMessage, type BridgeOptions, type GenericBridge } from './index.js';

export interface BridgeState<T> {
  bridge: T | null;
  ready: boolean;
  error: Error | null;
}

export function useQgisBridge<T extends GenericBridge = GenericBridge>(
  objectName: string | BridgeOptions = 'bridge',
  options: BridgeOptions = {}
): BridgeState<T> {
  let React: any;
  try {
    React = (typeof window !== 'undefined' ? (window as any).React : null) || 
            (typeof globalThis !== 'undefined' ? (globalThis as any).React : null);
  } catch {}

  if (!React) {
    console.warn('[qgis-bridge/react] React not found globally — use createBridge() directly or ensure React is loaded before this hook');
    return { bridge: null, ready: false, error: new Error('React not found') };
  }

  const [bridge, setBridge] = React.useState(null);
  const [ready, setReady] = React.useState(false);
  const [error, setError] = React.useState(null);

  React.useEffect(() => {
    const opts: BridgeOptions = typeof objectName === 'string' ? { objectName, ...options } : objectName;
    
    (createBridge as any)(opts)
      .then((b: any) => {
        setBridge(b);
        setReady(true);
      })
      .catch((err: any) => {
        console.error('[qgis-bridge/react] Failed to create bridge', err);
        setError(err as Error);
      });
  }, [typeof objectName === 'string' ? objectName : JSON.stringify(objectName)]);

  return { bridge, ready, error } as BridgeState<T>;
}

export function createReactHook<T extends GenericBridge = GenericBridge>(React: any) {
  return function useQgisBridgeTyped(
    objectName: string | BridgeOptions = 'bridge',
    options: BridgeOptions = {}
  ): BridgeState<T> {
    const [bridge, setBridge] = React.useState(null);
    const [ready, setReady] = React.useState(false);
    const [error, setError] = React.useState(null);

    React.useEffect(() => {
      const opts: BridgeOptions = typeof objectName === 'string' ? { objectName, ...options } : objectName;
      
      import('./index.js').then(({ createBridge }) => {
        (createBridge as any)(opts)
          .then((b: any) => {
            setBridge(b);
            setReady(true);
          })
          .catch((err: any) => setError(err as Error));
      });
    }, [typeof objectName === 'string' ? objectName : JSON.stringify(objectName)]);

    return { bridge, ready, error } as BridgeState<T>;
  };
}

export function useQgisMessage<T = any>(handler: (data: T) => void) {
  let React: any;
  try {
    React = (typeof window !== 'undefined' ? (window as any).React : null);
  } catch {}

  if (!React) {
    console.warn('[qgis-bridge/react] React not found for useQgisMessage');
    return;
  }

  React.useEffect(() => {
    return onQgisMessage(handler);
  }, [handler]);
}

export default useQgisBridge;
