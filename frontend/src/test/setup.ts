import '@testing-library/jest-dom';
import { afterEach } from 'vitest';
import { clearCrossTabState } from '../services/authSync';

// Ensure Web Locks API is available in JSDOM test environment
if (typeof window !== 'undefined' && !window.navigator.locks) {
  const nativeLocks = (globalThis as { navigator?: { locks?: unknown } }).navigator?.locks;
  if (nativeLocks) {
    Object.defineProperty(window.navigator, 'locks', {
      value: nativeLocks,
      configurable: true,
      writable: true,
    });
  } else {
    // FIFO Web Lock coordinator simulation for JSDOM
    const lockQueues = new Map<string, Array<() => void>>();
    Object.defineProperty(window.navigator, 'locks', {
      value: {
        request: async <T>(name: string, callback: () => Promise<T>): Promise<T> => {
          const acquirePromise = new Promise<void>((resolve) => {
            const queue = lockQueues.get(name) || [];
            lockQueues.set(name, queue);
            queue.push(resolve);
            if (queue.length === 1) {
              resolve();
            }
          });

          await acquirePromise;
          try {
            return await callback();
          } finally {
            const queue = lockQueues.get(name);
            if (queue) {
              queue.shift();
              if (queue.length > 0) {
                queue[0]();
              } else {
                lockQueues.delete(name);
              }
            }
          }
        },
      },
      configurable: true,
      writable: true,
    });
  }
}

afterEach(() => {
  clearCrossTabState();
});
