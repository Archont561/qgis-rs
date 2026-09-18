/** qgis-sdk-bridge description loader — loads BridgeDescription JSON from Python */

export interface MethodDescription {
  name: string;
  args: string[];
  arg_types: string[];
  return_type: string;
  doc?: string;
  is_signal?: boolean;
  is_slot?: boolean;
  is_property?: boolean;
}

export interface BridgeDescription {
  name: string;
  methods: MethodDescription[];
  signals: MethodDescription[];
  properties?: MethodDescription[];
  version: string;
  doc?: string;
}

export function loadDescription(): BridgeDescription | null {
  if (typeof window === 'undefined') return null;
  return (window as any).__QGIS_BRIDGE_DESCRIPTION__ || null;
}

export function loadQgisApiDescription(): BridgeDescription | null {
  if (typeof window === 'undefined') return null;
  return (window as any).__QGIS_API_DESCRIPTION__ || null;
}

export function loadBridgeName(): string {
  if (typeof window === 'undefined') return 'bridge';
  return (window as any).__QGIS_BRIDGE_NAME__ || 'bridge';
}

export function loadQgisApiName(): string {
  if (typeof window === 'undefined') return 'qgis';
  return (window as any).__QGIS_API_NAME__ || 'qgis';
}

export function createBridgeFromDescription<T>(desc: BridgeDescription, rawBridge: any): T {
  // Dynamically creates methods based on description if rawBridge doesn't have them
  // In QWebChannel, rawBridge already has methods, but we can add typed wrappers
  const result: any = {};
  
  // Copy raw methods
  if (rawBridge) {
    Object.keys(rawBridge).forEach(k => {
      if (typeof rawBridge[k] === 'function') {
        result[k] = (...args: any[]) => {
          return new Promise((resolve, reject) => {
            try {
              const lastArg = args[args.length - 1];
              const hasCallback = typeof lastArg === 'function';
              if (hasCallback) {
                rawBridge[k](...args);
              } else {
                rawBridge[k](...args, (res: any) => {
                  try {
                    if (typeof res === 'string') {
                      try {
                        const parsed = JSON.parse(res);
                        resolve(parsed);
                        return;
                      } catch {}
                    }
                    resolve(res);
                  } catch (e) {
                    reject(e);
                  }
                });
              }
            } catch (e) {
              reject(e);
            }
          });
        };
      } else {
        result[k] = rawBridge[k];
      }
    });
  }

  // Ensure methods from description exist (even if not in raw, create stub that calls via call())
  desc.methods.forEach(m => {
    if (!result[m.name]) {
      result[m.name] = (...args: any[]) => {
        if (rawBridge && typeof rawBridge[m.name] === 'function') {
          return result[m.name](...args);
        }
        // Fallback: try rawBridge.call or throw
        console.warn(`[qgis-bridge] Method ${m.name} not found in raw bridge, but in description`);
        return Promise.reject(new Error(`Method ${m.name} not found`));
      };
    }
  });

  return result as T;
}

export function descriptionToTypeScript(desc: BridgeDescription, interfaceName: string = 'Bridge'): string {
  const lines: string[] = [];
  lines.push(`/** Auto-generated from Python bridge ${desc.name} v${desc.version} */`);
  lines.push(`export interface ${interfaceName} {`);
  desc.methods.forEach(m => {
    const params = m.args.map((arg, i) => `${arg}: ${m.arg_types[i] || 'any'}`).join(', ');
    lines.push(`  ${m.name}(${params}): Promise<${m.return_type || 'any'}>;`);
  });
  lines.push('}');
  if (desc.signals.length > 0) {
    lines.push('');
    lines.push(`// Signals — connect via bridge.signal.connect(callback) or addEventListener`);
    desc.signals.forEach(s => {
      const params = s.args.map((arg, i) => `${arg}: ${s.arg_types[i] || 'any'}`).join(', ');
      lines.push(`// signal: ${s.name}(${params})`);
    });
  }
  return lines.join('\n');
}
