/**
 * loader.ts — auto-inject qrc:///qtwebchannel/qwebchannel.js with fallbacks
 * 
 * Qt provides built-in qwebchannel.js at qrc:///qtwebchannel/qwebchannel.js
 * This loader tries:
 * 1. If QWebChannel already global, use it
 * 2. qrc:///qtwebchannel/qwebchannel.js (Qt built-in, works in QGIS)
 * 3. ./qwebchannel.js (local bundle)
 * 4. CDN fallback (for dev outside QGIS)
 */

declare global {
  interface Window {
    QWebChannel?: any;
    qt?: any;
  }
  var QWebChannel: any;
  var qt: any;
}

export const QWEBCHANNEL_SOURCES = [
  'qrc:///qtwebchannel/qwebchannel.js',
  './qwebchannel.js',
  './web/qwebchannel.js',
  '/qwebchannel.js',
  'https://cdn.jsdelivr.net/npm/qwebchannel@6.1.0/qwebchannel.js',
  'https://unpkg.com/qwebchannel@1.0.0/qwebchannel.js',
] as const;

export function isQWebChannelAvailable(): boolean {
  return typeof (typeof window !== 'undefined' ? (window as any).QWebChannel : globalThis.QWebChannel) !== 'undefined' ||
         typeof QWebChannel !== 'undefined';
}

export function loadQWebChannel(sources: string[] = [...QWEBCHANNEL_SOURCES]): Promise<void> {
  return new Promise((resolve, reject) => {
    if (isQWebChannelAvailable()) {
      resolve();
      return;
    }

    if (typeof document === 'undefined') {
      // Not in browser (SSR, tests) — resolve, QWebChannel will be mocked
      resolve();
      return;
    }

    let idx = 0;

    function tryLoad() {
      if (idx >= sources.length) {
        reject(new Error(
          `Failed to load qwebchannel.js from any source. Tried: ${sources.join(', ')}. ` +
          `In QGIS, ensure you have <script src="qrc:///qtwebchannel/qwebchannel.js"></script> or use @qgis-sdk/bridge which auto-injects it.`
        ));
        return;
      }

      const src = sources[idx];
      const script = document.createElement('script');
      script.src = src;
      script.async = true;
      
      script.onload = () => {
        if (isQWebChannelAvailable()) {
          resolve();
        } else {
          idx++;
          tryLoad();
        }
      };
      
      script.onerror = () => {
        console.warn(`[qgis-bridge] Failed to load ${src}, trying next...`);
        idx++;
        tryLoad();
      };

      document.head.appendChild(script);
    }

    tryLoad();
  });
}

// Auto-load on import in browser, but don't block
if (typeof document !== 'undefined') {
  // Don't auto-load immediately — let createBridge trigger it
  // This avoids loading in contexts where it's not needed
}

export default loadQWebChannel;
