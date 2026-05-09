// Mirror of connectors/util.py — `retried_failed_network_request` higher-order
// wrapper. We use ccxt's exported error classes for retry classification.

import ccxt from "ccxt";
import { RetriableFailedRequest, RetriableExchangeProxyError } from "../errors.js";
import { sleep } from "../util/asyncTools.js";
import { getLogger } from "../util/logger.js";

const DEFAULT_RETRY_ATTEMPTS = 3;
const DEFAULT_RETRY_DELAY_SECONDS = 1;
const DEFAULT_PROXY_RETRY_ATTEMPTS = 1;

const RETRIABLE_EXCHANGE_ERRORS_DESC: string[] = [
  // From octobot_trading.constants.RETRIABLE_EXCHANGE_ERRORS_DESC
  "Internal server error",
  "Service unavailable",
  "Too many requests",
];

const logger = getLogger("retriedFailedNetworkRequest");

export interface RetryOptions {
  attempts?: number;
  retriableProxyErrorsAttempts?: number;
  delaySeconds?: number;
}

export function retriedFailedNetworkRequest<TArgs extends unknown[], TReturn>(
  fn: (...args: TArgs) => Promise<TReturn>,
  opts: RetryOptions = {},
): (...args: TArgs) => Promise<TReturn> {
  const attempts = opts.attempts ?? DEFAULT_RETRY_ATTEMPTS;
  const proxyAttempts = opts.retriableProxyErrorsAttempts ?? DEFAULT_PROXY_RETRY_ATTEMPTS;
  const delaySeconds = opts.delaySeconds ?? DEFAULT_RETRY_DELAY_SECONDS;

  return async (...args: TArgs): Promise<TReturn> => {
    let proxyErrorAttempts = 0;
    let lastErr: unknown = null;
    for (let attempt = 0; attempt < attempts; attempt++) {
      try {
        const resp = await fn(...args);
        if (attempt > 0) {
          logger.info(`${fn.name || "request"} succeeded after ${attempt + 1} attempts.`);
        }
        return resp;
      } catch (err) {
        lastErr = err;
        const isRetriable =
          err instanceof ccxt.RequestTimeout ||
          err instanceof ccxt.ExchangeNotAvailable ||
          err instanceof ccxt.InvalidNonce ||
          err instanceof RetriableFailedRequest ||
          err instanceof RetriableExchangeProxyError;
        const isProxy = err instanceof RetriableExchangeProxyError;
        const isExchangeError = err instanceof ccxt.ExchangeError;

        if (isProxy) {
          if (proxyErrorAttempts >= proxyAttempts - 1) {
            logger.warning(
              `${fn.name || "request"} raised proxy error (proxy attempts ${proxyErrorAttempts + 1}/${proxyAttempts}). Aborting.`,
            );
            throw err;
          }
          proxyErrorAttempts += 1;
        }

        if (isExchangeError && !isRetriable) {
          const msg = (err as Error).message || "";
          const matchesRetriablePattern = RETRIABLE_EXCHANGE_ERRORS_DESC.some((m) => msg.includes(m));
          if (!matchesRetriablePattern) throw err;
        } else if (!isRetriable && !isExchangeError) {
          throw err;
        }

        if (attempt >= attempts - 1) throw err;

        logger.warning(
          `${fn.name || "request"} raised ${(err as Error).message} (attempts ${attempt + 1}/${attempts}). Retrying in ${delaySeconds}s.`,
        );
        await sleep(delaySeconds * 1000);
      }
    }
    throw lastErr;
  };
}
