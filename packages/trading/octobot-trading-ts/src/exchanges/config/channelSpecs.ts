// Mirror of config/channel_specs.py — used as a typed identifier on the WS
// EventBus to disambiguate (channel, symbol, timeframe) topics.

export interface ChannelSpecs {
  channel: string;
  symbol?: string;
  timeFrame?: string;
}

export function channelKey(spec: ChannelSpecs): string {
  return `${spec.channel}|${spec.symbol ?? ""}|${spec.timeFrame ?? ""}`;
}
