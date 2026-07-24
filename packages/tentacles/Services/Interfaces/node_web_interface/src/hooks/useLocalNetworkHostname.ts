import { useQuery } from "@tanstack/react-query"

import { SetupService } from "@/client"

function isUsableBrowserHostname(hostname: string): boolean {
  return hostname !== "localhost" && hostname !== "127.0.0.1"
}

export function useLocalNetworkHostname() {
  const localNetworkQuery = useQuery({
    queryKey: ["setup", "local-network-address"],
    queryFn: () => SetupService.getLocalNetworkAddress(),
  })

  const browserHostname = window.location.hostname
  const detectedIp = localNetworkQuery.data?.local_network_ip ?? null
  const fallbackHostname = isUsableBrowserHostname(browserHostname)
    ? browserHostname
    : ""

  const hostname = detectedIp ?? fallbackHostname
  const couldNotDetect =
    !localNetworkQuery.isPending &&
    !detectedIp &&
    !isUsableBrowserHostname(browserHostname)
  const hostnameHelperText = couldNotDetect
    ? "Could not detect your local network IP. Find it in your system network settings."
    : undefined

  return {
    hostname,
    hostnameHelperText,
    isPending: localNetworkQuery.isPending,
    isError: localNetworkQuery.isError,
  }
}
