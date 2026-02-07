import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function getAssetPath(assetPath: string): string {
  const baseUrl = import.meta.env.BASE_URL
  const normalizedPath = assetPath.startsWith("/") ? assetPath.slice(1) : assetPath
  return `${baseUrl}assets/${normalizedPath}`
}
