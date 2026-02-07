/**
 * Concurrency limiter — single-key semaphore for sub-agent slots.
 *
 * Based on OMO's ConcurrencyManager, simplified for Kiwi's single-model use case.
 */

interface Waiter {
  resolve: () => void
  reject: (reason?: unknown) => void
  settled: boolean
}

export class ConcurrencyLimiter {
  private count = 0
  private queue: Waiter[] = []

  constructor(private readonly maxConcurrent: number) {}

  /** Acquire a slot. Resolves immediately if available, otherwise queues. */
  acquire(): Promise<void> {
    if (this.count < this.maxConcurrent) {
      this.count++
      return Promise.resolve()
    }
    return new Promise<void>((resolve, reject) => {
      this.queue.push({ resolve, reject, settled: false })
    })
  }

  /** Release a slot. Hands off to next waiter or decrements count. */
  release(): void {
    while (this.queue.length > 0) {
      const waiter = this.queue.shift()!
      if (waiter.settled) continue
      waiter.settled = true
      waiter.resolve()
      return
    }
    this.count = Math.max(0, this.count - 1)
  }

  /** Cancel all waiting acquires and reset count. */
  clear(): void {
    for (const waiter of this.queue) {
      if (!waiter.settled) {
        waiter.settled = true
        waiter.reject(new Error("ConcurrencyLimiter cleared"))
      }
    }
    this.queue = []
    this.count = 0
  }
}
