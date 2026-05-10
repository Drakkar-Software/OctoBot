// Hand-written TypeScript types derived from packages/protocol/openapi.json.
// Regenerate by running `npm run generate:typescript` in packages/protocol/ (requires Java).

export enum TaskStatus {
  Pending = "pending",
  Scheduled = "scheduled",
  Periodic = "periodic",
  Running = "running",
  Completed = "completed",
  Failed = "failed",
  Cancelled = "cancelled",
}

export interface ExecutionError {
  name?: string;
  message: string;
  stack?: string;
}

export interface Execution {
  id: string;
  automationId: string;
  reason: string;
  startedAt: number;
  completedAt?: number;
  status: TaskStatus;
  input?: { [key: string]: unknown };
  result?: { [key: string]: unknown };
  error?: ExecutionError;
}

// ---- Trading types (not consumed by node-ts but part of the protocol) ----

export type Side = "buy" | "sell";

export type OrderType = string;
export type OrderStatus = string;
export type PositionStatus = string;
export type TrailingProfileType = string;
export type CancelPolicyType = string;
export type ActiveOrderSwapStrategyType = string;
export type OrderGroupType = string;

export interface TrailingProfile {
  type?: TrailingProfileType;
  [key: string]: unknown;
}

export interface CancelPolicy {
  type?: CancelPolicyType;
  [key: string]: unknown;
}

export interface ActiveOrderSwapStrategy {
  type?: ActiveOrderSwapStrategyType;
  [key: string]: unknown;
}

export interface OrderGroup {
  type?: OrderGroupType;
  [key: string]: unknown;
}

export interface OrderSummary {
  id: string;
  symbol: string;
}

export interface TradeSummary {
  id: string;
  symbol: string;
}

export interface PositionSummary {
  id: string;
  symbol: string;
}

export interface Order {
  id: string;
  symbol: string;
  side: Side;
  type?: OrderType;
  quantity: number;
  price?: number;
  status?: OrderStatus;
  [key: string]: unknown;
}

export interface Trade {
  id: string;
  symbol: string;
  side: Side;
  quantity: number;
  price: number;
  fee?: number;
  [key: string]: unknown;
}

export interface Position {
  id: string;
  symbol: string;
  side: Side;
  quantity: number;
  entryPrice: number;
  markPrice: number;
  liquidationPrice: number;
  status: PositionStatus;
}

// ---- Asset ----

export interface Asset {
  symbol: string;
  total: number;
  available: number;
  value?: number;
  unit?: string;
}

export interface CopiedAsset {
  name: string;
  total: number;
  available: number;
  ratio: number;
}

// ---- Action types ----

export interface ActionBase {
  id: string;
  actionType: string;
  status: TaskStatus;
  dsl?: string;
  result?: string;
  error?: string;
  completedAt?: Date;
}

export interface AddExchangeAccountAction extends ActionBase {
  actionType: "add_exchange_account";
  account: Account;
}

export interface RemoveExchangeAccountAction extends ActionBase {
  actionType: "remove_exchange_account";
  accountId: string;
}

export interface AddAutomationAction extends ActionBase {
  actionType: "add_automation";
  automation: AutomationState;
}

export interface RemoveAutomationAction extends ActionBase {
  actionType: "remove_automation";
  automationId: string;
}

export type Action =
  | AddExchangeAccountAction
  | RemoveExchangeAccountAction
  | AddAutomationAction
  | RemoveAutomationAction;

// ---- Automation types ----

export interface AutomationMetadata {
  name: string;
  description: string;
  createdAt?: Date;
  updatedAt?: Date;
}

export interface AutomationState {
  id: string;
  status: TaskStatus;
  metadata: AutomationMetadata;
  actions?: Action[];
  priorityActions?: Action[];
  exchanges?: string[];
  exchangeAccountIds?: string[];
  assets?: Asset[];
  orders?: OrderSummary[];
  trades?: TradeSummary[];
  positions?: PositionSummary[];
  executions?: Execution[];
  lastExecution?: Execution;
}

export interface AutomationsState {
  version: string;
  automations?: AutomationState[];
}

// ---- Account types ----

export interface ExchangeAccount {
  exchange: string;
  remoteAccountId: string;
  apiKey: string;
  apiSecret: string;
  apiPassphrase?: string;
  assets?: Asset[];
  orders?: Order[];
  trades?: Trade[];
  positions?: Position[];
}

export interface BlockchainAccount {
  blockchain: string;
  network?: string;
  publicKey?: string;
  privateKey?: string;
  passphrase?: string;
}

export interface GenericAccount {
  assets?: Asset[];
}

export enum AccountType {
  Generic = "GENERIC",
  Exchange = "EXCHANGE",
  Blockchain = "BLOCKCHAIN",
}

export interface Account {
  id: string;
  accountType: AccountType;
  name: string;
  isSimulated: boolean;
  description?: string;
  createdAt?: Date;
  updatedAt?: Date;
  exchangeAccount?: ExchangeAccount | null;
  blockchainAccount?: BlockchainAccount | null;
  genericAccount?: GenericAccount | null;
}

export interface AccountsState {
  version: string;
  accounts?: Account[];
}

export interface CopiedAccount {
  version: string;
  updatedAt: Date;
  copiedAssets: CopiedAsset[];
}
