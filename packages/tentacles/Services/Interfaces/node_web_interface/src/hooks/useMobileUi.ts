import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import { MobileUiService } from "@/client"
import {
  MOBILE_UI_STATUS_POLL_MS,
  MOBILE_UI_STATUS_QUERY_KEY,
  shouldPollMobileUi,
} from "@/lib/mobile-ui"

export function useMobileUi() {
  const queryClient = useQueryClient()

  const statusQuery = useQuery({
    queryKey: MOBILE_UI_STATUS_QUERY_KEY,
    queryFn: () => MobileUiService.getMobileUiStatus().catch(() => null),
    refetchInterval: (query) =>
      shouldPollMobileUi(query.state.data ?? undefined)
        ? MOBILE_UI_STATUS_POLL_MS
        : false,
    retry: false,
    refetchOnWindowFocus: false,
  })

  const checkMutation = useMutation({
    mutationFn: () => MobileUiService.checkMobileUiUpdate(),
    onSuccess: (status) => {
      queryClient.setQueryData(MOBILE_UI_STATUS_QUERY_KEY, status)
    },
    onError: (error) => {
      console.error("useMobileUi: check request failed", error)
      void queryClient.invalidateQueries({ queryKey: MOBILE_UI_STATUS_QUERY_KEY })
    },
  })

  const installMutation = useMutation({
    mutationFn: () => MobileUiService.installMobileUi(),
    onSuccess: (status) => {
      queryClient.setQueryData(MOBILE_UI_STATUS_QUERY_KEY, status)
    },
    onError: (error) => {
      console.error("useMobileUi: install request failed", error)
      void queryClient.invalidateQueries({ queryKey: MOBILE_UI_STATUS_QUERY_KEY })
    },
  })

  return {
    status: statusQuery.data ?? undefined,
    isLoading: statusQuery.isPending,
    check: checkMutation.mutate,
    isCheckRequestPending: checkMutation.isPending,
    checkSucceeded: checkMutation.isSuccess,
    install: () => {
      checkMutation.reset()
      installMutation.mutate()
    },
    isInstallRequestPending: installMutation.isPending,
    installRequestFailed: installMutation.isError,
  }
}
