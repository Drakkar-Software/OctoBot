// Stub of octobot_trading.accounts.AbstractAccount.
// In the Python source, this base class wires up account-level features
// (account type, sub-account selection, authentication state) shared between
// real exchanges and account-like wrappers. The browser-facing TS port keeps
// only the fields/methods that AbstractExchange inherits and reads from.

export class AbstractAccount {
  isAuthenticated = false;

  // Subclasses can override.
  loadUserInputsFromClass(_setupConfig: unknown, _tentacleConfig: unknown): void {
    // no-op: tentacle setup is server-side
  }

  getTentacleConfig(_byExchange: Record<string, Record<string, unknown>>): Record<string, unknown> | null {
    return null;
  }
}
