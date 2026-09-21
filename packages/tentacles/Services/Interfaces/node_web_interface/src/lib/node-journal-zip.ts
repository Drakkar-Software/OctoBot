import { zipSync } from "fflate"

export type ZipArchiveMember = {
  name: string
  data: Uint8Array
}

/** Build a Deflate-compressed ZIP archive. */
export function buildZipArchive(members: ZipArchiveMember[]): Uint8Array {
  const files: Record<string, Uint8Array> = {}
  for (const member of members) {
    files[member.name] = member.data
  }
  return zipSync(files, { level: 6 })
}
