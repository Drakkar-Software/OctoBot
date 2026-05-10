import { describe, it, expect } from "vitest";
import { emptyAccountsState, findAccount, replaceAccount } from "../src/accounts.js";
import type { Account } from "@drakkarsoftware/octobot-protocol";
import { AccountType } from "@drakkarsoftware/octobot-protocol";

const account = (id: string, extra?: Partial<Account>): Account => ({
  id,
  accountType: AccountType.Exchange,
  name: id,
  isSimulated: false,
  ...extra,
});

describe("accounts state helpers", () => {
  it("emptyAccountsState returns valid protocol shape", () => {
    const s = emptyAccountsState();
    expect(s.version).toBeTruthy();
    expect(s.accounts).toEqual([]);
  });

  it("findAccount returns account by id or null", () => {
    const s = { ...emptyAccountsState(), accounts: [account("a"), account("b")] };
    expect(findAccount(s, "a")?.id).toBe("a");
    expect(findAccount(s, "b")?.id).toBe("b");
    expect(findAccount(s, "missing")).toBeNull();
  });

  it("replaceAccount is immutable — original state unchanged", () => {
    const original = { ...emptyAccountsState(), accounts: [account("a")] };
    const updated = replaceAccount(original, account("a", { name: "updated" }));
    expect(original.accounts![0].name).toBe("a");
    expect(updated.accounts![0].name).toBe("updated");
    expect(updated).not.toBe(original);
  });

  it("replaceAccount replaces at the correct index without touching others", () => {
    const a = account("a");
    const b = account("b");
    const c = account("c");
    const original = { ...emptyAccountsState(), accounts: [a, b, c] };
    const updated = replaceAccount(original, account("b", { name: "b-new" }));
    expect(updated.accounts![0]).toBe(a);
    expect(updated.accounts![1].name).toBe("b-new");
    expect(updated.accounts![2]).toBe(c);
  });

  it("replaceAccount appends when id not found", () => {
    const s = { ...emptyAccountsState(), accounts: [account("a")] };
    const updated = replaceAccount(s, account("z"));
    expect(updated.accounts).toHaveLength(2);
    expect(updated.accounts![1].id).toBe("z");
  });
});
