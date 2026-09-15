import { describe, it, expect } from 'vitest'
import { describeProposedAction } from '../src/protocol/proposalSummary.js'

describe('describeProposedAction', () => {
  it('humanizes the action_type when there is no nested name', () => {
    expect(describeProposedAction({ action_type: 'automation_stop', id: 'auto_1' } as never)).toBe('automation stop')
  })

  it('appends the nested configuration name when present', () => {
    expect(describeProposedAction({
      action_type: 'account_create',
      configuration: { name: 'Binance' },
    } as never)).toBe('account create — "Binance"')
  })

  it('falls back to a generic label when action_type is missing', () => {
    expect(describeProposedAction({} as never)).toBe('action')
  })

  // Regression pin: account_auth_create/edit configurations carry api_key/
  // api_secret/api_passphrase verbatim (see the client's account-auth
  // builders). This runs in both the mobile share-action flow and the node
  // web interface's paste dialog, so it must never surface those fields even
  // if the shape grows a 'label'/'title' key that could collide — only
  // `name` is read.
  it('never reads or surfaces credential fields, even when present on the configuration', () => {
    const result = describeProposedAction({
      action_type: 'account_auth_create',
      configuration: {
        id: 'auth_exchange_1', api_key: 'SECRET_KEY_1', api_secret: 'SECRET_VALUE_1',
        api_passphrase: 'SECRET_PASSPHRASE_1', name: 'not-a-real-field-but-checked-too',
      },
    } as never)
    expect(result).not.toContain('SECRET_KEY_1')
    expect(result).not.toContain('SECRET_VALUE_1')
    expect(result).not.toContain('SECRET_PASSPHRASE_1')
  })
})
