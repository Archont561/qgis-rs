/** qgis-sdk-bridge loader — auto-injects qwebchannel.js */

export const QWEBCHANNEL_SOURCES = [
  'qrc:///qtwebchannel/qwebchannel.js',
  './qwebchannel.js',
  '/qwebchannel.js',
  'https://cdn.jsdelivr.net/npm/qwebchannel@6.1.0/qwebchannel.js'
];

export function isQWebChannelAvailable(): boolean {
  if (typeof window !== 'undefined' && (window as any).QWebChannel) return true;
  if (typeof (globalThis as any).QWebChannel !== 'undefined') return true;
  return false;
}

export function loadQWebChannel(customSources?: string[]): Promise<void> {
  const sources = customSources || QWEBCHANNEL_SOURCES;
  
  return new Promise((resolve, reject) => {
    if (isQWebChannelAvailable()) {
      resolve();
      return;
    }

    if (typeof document === 'undefined') {
      // Not in browser — for bun test or SSR, resolve without loading
      resolve();
      return;
    }

    let idx = 0;
    
    function tryLoad() {
      if (idx >= sources.length) {
        reject(new Error(`Failed to load qwebchannel.js from any source: ${sources.join(', ')}`));
        return;
      }

      const src = sources[idx];
      const script = document.createElement('script');
      script.src = src;
      script.onload = () => {
        if (isQWebChannelAvailable()) {
          console.log(`[qgis-bridge] Loaded qwebchannel.js from ${src}`);
          resolve();
        } else {
          console.warn(`[qgis-bridge] Loaded ${src} but QWebChannel not found, trying next`);
          idx++;
          tryLoad();
        }
      };
      script.onerror = () => {
        console.warn(`[qgis-bridge] Failed to load ${src}, trying next`);
        idx++;
        tryLoad();
      };
      document.head.appendChild(script);
    }

    tryLoad();
  });
}

// For backwards compat
export const loadQwebchannel = loadQWebChannel;
