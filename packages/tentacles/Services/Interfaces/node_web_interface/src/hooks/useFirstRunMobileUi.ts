import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import { type ApiError, MobileUiService } from "@/client"
import {
  FIRST_RUN_MOBILE_UI_QUERY_KEY,
  FIRST_RUN_MOBILE_UI_POLL_MS,
  shouldPollFirstRunMobileUi,
} from "@/lib/first-run-mobile-ui"

export type UseFirstRunMobileUiOptions = {
  /** Fetch first-run mobile-ui status (Welcome choose / downloading / failed). */
  statusEnabled?: boolean
  /** Poll continuously while the welcome flow is in the downloading phase. */
  downloadInProgress?: boolean
}

export function useFirstRunMobileUi(options?: UseFirstRunMobileUiOptions) {
  const queryClient = useQueryClient()
  const statusEnabled = options?.statusEnabled ?? true
  const downloadInProgress = options?.downloadInProgress ?? false

  const statusQuery = useQuery({
    queryKey: FIRST_RUN_MOBILE_UI_QUERY_KEY,
    queryFn: () => MobileUiService.getMobileUiFirstRunStatus(),
    enabled: statusEnabled,
    refetchInterval: (query) =>
      statusEnabled &&
      shouldPollFirstRunMobileUi(query.state.data ?? undefined, {
        downloadInProgress,
      })
        ? FIRST_RUN_MOBILE_UI_POLL_MS
        : false,
    retry: (failureCount, error) => {
      const apiError = error as ApiError
      if (apiError.status === 409) {
        return false
      }
      return failureCount < 1
    },
    refetchOnWindowFocus: false,
  })

  const installMutation = useMutation({
    mutationFn: () => MobileUiService.installMobileUiFirstRun(),
    onMutate: async () => {
      await queryClient.cancelQueries({ queryKey: FIRST_RUN_MOBILE_UI_QUERY_KEY })
    },
    onSuccess: (status) => {
      queryClient.setQueryData(FIRST_RUN_MOBILE_UI_QUERY_KEY, status)
    },
    onError: (error) => {
      const apiError = error as ApiError
      if (apiError.status === 409) {
        void queryClient.invalidateQueries({ queryKey: FIRST_RUN_MOBILE_UI_QUERY_KEY })
        return
      }
      console.error("useFirstRunMobileUi: install request failed", error)
      void queryClient.invalidateQueries({ queryKey: FIRST_RUN_MOBILE_UI_QUERY_KEY })
    },
  })

  const firstRunConflict =
    (statusQuery.error as ApiError | undefined)?.status === 409 ||
    (installMutation.error as ApiError | undefined)?.status === 409

  return {
    status: statusQuery.data ?? undefined,
    isStatusLoading: statusQuery.isPending,
    statusError: statusQuery.error,
    firstRunConflict,
    install: () => installMutation.mutate(),
    isInstallPending: installMutation.isPending,
    installError: installMutation.error,
  }
}