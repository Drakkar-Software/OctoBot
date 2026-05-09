// Tiny EventEmitter-style bus. Listeners that need async work should kick off
// their own promise; we don't await them so a slow consumer can't stall the
// producer.

export type Listener<TPayload = unknown> = (payload: TPayload) => void;

export class EventBus {
  private listeners: Map<string, Set<Listener>> = new Map();

  on<T = unknown>(topic: string, listener: Listener<T>): () => void {
    let set = this.listeners.get(topic);
    if (!set) {
      set = new Set();
      this.listeners.set(topic, set);
    }
    set.add(listener as Listener);
    return () => this.off(topic, listener);
  }

  off<T = unknown>(topic: string, listener: Listener<T>): void {
    const set = this.listeners.get(topic);
    if (set) set.delete(listener as Listener);
  }

  emit<T = unknown>(topic: string, payload: T): void {
    const set = this.listeners.get(topic);
    if (!set) return;
    for (const l of set) {
      try {
        l(payload);
      } catch (err) {
        console.error(`[octobot-commons] listener for "${topic}" threw:`, err);
      }
    }
  }

  removeAllListeners(topic?: string): void {
    if (topic) this.listeners.delete(topic);
    else this.listeners.clear();
  }
}
