export const AutomationWorkflowActionType = {
  UserActions: "user_actions",
  TradingSignal: "trading_signal",
  ForcedTrigger: "forced_trigger",
} as const;

export type AutomationWorkflowActionType =
  typeof AutomationWorkflowActionType[keyof typeof AutomationWorkflowActionType];
