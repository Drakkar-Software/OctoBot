import { useQuery } from "@tanstack/react-query"

import { SetupService } from "@/client"

export function useVpnNetworkHostname() {
  const vpnNetworkQuery = useQuery({
    queryKey: ["setup", "vpn-network-address"],
    queryFn: () => SetupService.getVpnNetworkAddress(),
  })

  const detectedIp = vpnNetworkQuery.data?.vpn_network_ip ?? null
  const hostname = detectedIp ?? ""
  const couldNotDetect = !vpnNetworkQuery.isPending && !detectedIp

  return {
    hostname,
    couldNotDetect,
    isPending: vpnNetworkQuery.isPending,
    isFetching: vpnNetworkQuery.isFetching,
    isError: vpnNetworkQuery.isError,
    refresh: () => vpnNetworkQuery.refetch(),
  }
}
