import { memo, useCallback, useState } from "react"

import type {
  Account,
  AccountTradingWithAccountId,
  AutomationState,
  ExchangeConfig,
  Strategy,
  UserAction,
} from "@/client"
import { DebugTabDeleteControls } from "@/components/Debug/DebugTabDeleteControls"
import { AccountsTable } from "@/components/Debug/tables/AccountsTable"
import { AutomationsTable } from "@/components/Debug/tables/AutomationsTable"
import { ExchangeConfigsTable } from "@/components/Debug/tables/ExchangeConfigsTable"
import { StrategiesTable } from "@/components/Debug/tables/StrategiesTable"
import { UserActionsTable } from "@/components/Debug/tables/UserActionsTable"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { DEBUG_DELETABLE_TAB_VALUES } from "@/lib/debug/constants"
import type { ExecuteActionDraft } from "@/lib/debug/types"
import {
  buildAccountEditUserActionJson,
  buildAutomationCreateUserActionJsonForAccount,
  buildAutomationCreateUserActionJsonForStrategy,
  buildAutomationSignalUserActionJson,
  buildAutomationStopUserActionJson,
  buildExchangeConfigEditUserActionJson,
  buildStrategyEditUserActionJson,
} from "@/lib/debug/user-action-templates"

const DELETABLE_TABS = new Set<string>(DEBUG_DELETABLE_TAB_VALUES)

type DebugTabsPanelProps = {
  isImportedMode: boolean
  walletQueryParam?: string
  automations: AutomationState[]
  userActions: UserAction[]
  accounts: Account[]
  exchangeConfigs: ExchangeConfig[]
  accountTradings: AccountTradingWithAccountId[]
  localStrategies: Strategy[]
  onRefresh: () => void
  onOpenExecuteAction: (draft?: ExecuteActionDraft) => void
}

function DebugTabsPanelComponent({
  isImportedMode,
  walletQueryParam,
  automations,
  userActions,
  accounts,
  exchangeConfigs,
  accountTradings,
  localStrategies,
  onRefresh,
  onOpenExecuteAction,
}: DebugTabsPanelProps) {
  const [activeTab, setActiveTab] = useState("automations")
  const [deleteMode, setDeleteMode] = useState(false)
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())

  const isDeletableTab = DELETABLE_TABS.has(activeTab)
  const canDelete = isDeletableTab && !isImportedMode

  const handleTabChange = (tab: string) => {
    setActiveTab(tab)
    if (!DELETABLE_TABS.has(tab)) {
      setDeleteMode(false)
      setSelectedIds(new Set())
    }
  }

  const handleToggleRow = useCallback((id: string) => {
    setSelectedIds((previous) => {
      const next = new Set(previous)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }, [])

  const handleToggleAllVisible = useCallback(
    (ids: string[], select: boolean) => {
      setSelectedIds((previous) => {
        const next = new Set(previous)
        for (const id of ids) {
          if (select) next.add(id)
          else next.delete(id)
        }
        return next
      })
    },
    [],
  )

  const handleEnterDeleteMode = () => {
    setDeleteMode(true)
    setSelectedIds(new Set())
  }

  const handleCancelDeleteMode = () => {
    setDeleteMode(false)
    setSelectedIds(new Set())
  }

  const handleDeleted = () => {
    setDeleteMode(false)
    setSelectedIds(new Set())
    onRefresh()
  }

  return (
    <Tabs value={activeTab} onValueChange={handleTabChange}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <TabsList className="flex h-auto flex-wrap gap-1">
          <TabsTrigger value="automations">
            Automations ({automations.length})
          </TabsTrigger>
          <TabsTrigger value="user-actions">
            User actions ({userActions.length})
          </TabsTrigger>
          <TabsTrigger value="accounts">
            Accounts ({accounts.length})
          </TabsTrigger>
          <TabsTrigger value="exchange-configs">
            Exchange configs ({exchangeConfigs.length})
          </TabsTrigger>
          <TabsTrigger value="strategies">
            Strategies ({localStrategies.length})
          </TabsTrigger>
        </TabsList>
        <DebugTabDeleteControls
          deleteMode={deleteMode}
          canDelete={canDelete}
          selectedCount={selectedIds.size}
          selectedIds={selectedIds}
          onEnterDeleteMode={handleEnterDeleteMode}
          onCancelDeleteMode={handleCancelDeleteMode}
          onDeleted={handleDeleted}
        />
      </div>
      <TabsContent value="automations" className="mt-4">
        <AutomationsTable
          rows={automations}
          readOnly={isImportedMode}
          walletAddress={isImportedMode ? undefined : walletQueryParam}
          accountTradings={accountTradings}
          onSuccess={isImportedMode ? undefined : onRefresh}
          selectionMode={deleteMode && activeTab === "automations"}
          selectedIds={selectedIds}
          onToggleRow={handleToggleRow}
          onToggleAllVisible={handleToggleAllVisible}
          onSignal={
            isImportedMode
              ? (automation) =>
                  onOpenExecuteAction({
                    actionType: "automation_signal",
                    jsonText: buildAutomationSignalUserActionJson(
                      automation.id,
                    ),
                  })
              : undefined
          }
          onStop={(automation) =>
            onOpenExecuteAction({
              actionType: "automation_stop",
              jsonText: buildAutomationStopUserActionJson(automation.id),
            })
          }
        />
      </TabsContent>
      <TabsContent value="user-actions" className="mt-4">
        <UserActionsTable
          rows={userActions}
          selectionMode={deleteMode && activeTab === "user-actions"}
          selectedIds={selectedIds}
          onToggleRow={handleToggleRow}
          onToggleAllVisible={handleToggleAllVisible}
        />
      </TabsContent>
      <TabsContent value="accounts" className="mt-4">
        <AccountsTable
          rows={accounts}
          exchangeConfigs={exchangeConfigs}
          accountTradings={accountTradings}
          onEdit={(account) =>
            onOpenExecuteAction({
              actionType: "account_edit",
              jsonText: buildAccountEditUserActionJson(account),
            })
          }
          onStartAutomation={(account) =>
            onOpenExecuteAction({
              actionType: "automation_create",
              jsonText: buildAutomationCreateUserActionJsonForAccount(account),
            })
          }
        />
      </TabsContent>
      <TabsContent value="exchange-configs" className="mt-4">
        <ExchangeConfigsTable
          rows={exchangeConfigs}
          accounts={accounts}
          onEdit={(config) =>
            onOpenExecuteAction({
              actionType: "exchange_config_edit",
              jsonText: buildExchangeConfigEditUserActionJson(config),
            })
          }
        />
      </TabsContent>
      <TabsContent value="strategies" className="mt-4">
        <StrategiesTable
          rows={localStrategies}
          onEdit={(strategy) =>
            onOpenExecuteAction({
              actionType: "strategy_edit",
              jsonText: buildStrategyEditUserActionJson(strategy),
            })
          }
          onStartAutomation={(strategy) =>
            onOpenExecuteAction({
              actionType: "automation_create",
              jsonText:
                buildAutomationCreateUserActionJsonForStrategy(strategy),
            })
          }
        />
      </TabsContent>
    </Tabs>
  )
}

export const DebugTabsPanel = memo(DebugTabsPanelComponent)
