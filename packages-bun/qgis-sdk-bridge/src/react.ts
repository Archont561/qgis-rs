/**
 * React hooks for QGIS bridge — typed, window-like, with complete QGIS API
 * Built with bun
 */

import { createBridge, createQgisBridge, onQgisMessage, type QgisBridge } from './index.js';
import type { QgisAPI } from './qgis.js';
import type { BridgeOptions } from './window.js';

export interface BridgeState<T = QgisBridge> {
  bridge: (T & QgisBridge) | null;
  ready: boolean;
  error: Error | null;
}

export interface QgisState<T = QgisBridge> {
  bridge: (T & QgisBridge) | null;
  qgis: QgisAPI | null;
  ready: boolean;
  error: Error | null;
}

export function useQgisBridge<T = QgisBridge>(
  objectName: string | BridgeOptions = 'bridge',
  options: BridgeOptions = {}
): BridgeState<T> {
  let React: any;
  try {
    React = (typeof window !== 'undefined' ? (window as any).React : null) || 
            (typeof globalThis !== 'undefined' ? (globalThis as any).React : null);
  } catch {}

  if (!React) {
    console.warn('[qgis-bridge/react] React not found globally — use createBridge() directly');
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

export function useQgis<T = QgisBridge>(
  objectName: string | BridgeOptions = 'bridge',
  options: BridgeOptions = {}
): QgisState<T> {
  let React: any;
  try {
    React = (typeof window !== 'undefined' ? (window as any).React : null);
  } catch {}

  if (!React) {
    console.warn('[qgis-bridge/react] React not found for useQgis');
    return { bridge: null, qgis: null, ready: false, error: new Error('React not found') };
  }

  const [bridge, setBridge] = React.useState(null);
  const [qgis, setQgis] = React.useState(null);
  const [ready, setReady] = React.useState(false);
  const [error, setError] = React.useState(null);

  React.useEffect(() => {
    const opts: BridgeOptions = typeof objectName === 'string' ? { objectName, ...options } : objectName;
    
    (createQgisBridge as any)(opts)
      .then((res: any) => {
        setBridge(res.bridge);
        setQgis(res.qgis);
        setReady(true);
      })
      .catch((err: any) => {
        console.error('[qgis-bridge/react] Failed to create qgis bridge', err);
        setError(err as Error);
      });
  }, [typeof objectName === 'string' ? objectName : JSON.stringify(objectName)]);

  return { bridge, qgis, ready, error } as QgisState<T>;
}

export function createReactHook<T = QgisBridge>(React: any) {
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

export function createQgisReactHook<T = QgisBridge>(React: any) {
  return function useQgisTyped(
    objectName: string | BridgeOptions = 'bridge',
    options: BridgeOptions = {}
  ): QgisState<T> {
    const [bridge, setBridge] = React.useState(null);
    const [qgis, setQgis] = React.useState(null);
    const [ready, setReady] = React.useState(false);
    const [error, setError] = React.useState(null);

    React.useEffect(() => {
      const opts: BridgeOptions = typeof objectName === 'string' ? { objectName, ...options } : objectName;
      
      import('./index.js').then(({ createQgisBridge }) => {
        (createQgisBridge as any)(opts)
          .then((res: any) => {
            setBridge(res.bridge);
            setQgis(res.qgis);
            setReady(true);
          })
          .catch((err: any) => setError(err as Error));
      });
    }, [typeof objectName === 'string' ? objectName : JSON.stringify(objectName)]);

    return { bridge, qgis, ready, error } as QgisState<T>;
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
