import type { Account, AccountsState } from "@drakkarsoftware/octobot-protocol";

const PROTOCOL_VERSION = "1.0.0";

export function emptyAccountsState(): AccountsState {
  return { version: PROTOCOL_VERSION, accounts: [] };
}

export function findAccount(state: AccountsState, id: string): Account | null {
  return state.accounts?.find((a) => a.id === id) ?? null;
}

export function replaceAccount(state: AccountsState, account: Account): AccountsState {
  const accounts = state.accounts ?? [];
  const idx = accounts.findIndex((a) => a.id === account.id);
  if (idx < 0) return { ...state, accounts: [...accounts, account] };
  const next = accounts.slice();
  next[idx] = account;
  return { ...state, accounts: next };
}
