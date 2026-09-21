const CRC32_TABLE = (() => {
  const table = new Uint32Array(256)
  for (let index = 0; index < 256; index += 1) {
    let value = index
    for (let bit = 0; bit < 8; bit += 1) {
      value = value & 1 ? 0xedb88320 ^ (value >>> 1) : value >>> 1
    }
    table[index] = value >>> 0
  }
  return table
})()

function crc32(bytes: Uint8Array): number {
  let checksum = 0xffffffff
  for (let index = 0; index < bytes.length; index += 1) {
    checksum = CRC32_TABLE[(checksum ^ bytes[index]) & 0xff] ^ (checksum >>> 8)
  }
  return (checksum ^ 0xffffffff) >>> 0
}

function utf8Bytes(value: string): Uint8Array {
  return new TextEncoder().encode(value)
}

function writeUint16LE(view: DataView, offset: number, value: number): void {
  view.setUint16(offset, value, true)
}

function writeUint32LE(view: DataView, offset: number, value: number): void {
  view.setUint32(offset, value, true)
}

export type ZipArchiveMember = {
  name: string
  data: Uint8Array
}

/** Build a minimal ZIP archive (stored, no compression). */
export function buildStoredZipArchive(members: ZipArchiveMember[]): Uint8Array {
  const localParts: Uint8Array[] = []
  const centralParts: Uint8Array[] = []
  let offset = 0

  for (const member of members) {
    const nameBytes = utf8Bytes(member.name)
    const dataBytes = member.data
    const dataCrc = crc32(dataBytes)
    const localHeader = new Uint8Array(30 + nameBytes.length)
    const localView = new DataView(localHeader.buffer)
    writeUint32LE(localView, 0, 0x04034b50)
    writeUint16LE(localView, 4, 20)
    writeUint16LE(localView, 6, 0)
    writeUint16LE(localView, 8, 0)
    writeUint16LE(localView, 10, 0)
    writeUint16LE(localView, 12, 0)
    writeUint32LE(localView, 14, dataCrc)
    writeUint32LE(localView, 18, dataBytes.length)
    writeUint32LE(localView, 22, dataBytes.length)
    writeUint16LE(localView, 26, nameBytes.length)
    writeUint16LE(localView, 28, 0)
    localHeader.set(nameBytes, 30)
    localParts.push(localHeader, dataBytes)

    const centralHeader = new Uint8Array(46 + nameBytes.length)
    const centralView = new DataView(centralHeader.buffer)
    writeUint32LE(centralView, 0, 0x02014b50)
    writeUint16LE(centralView, 4, 20)
    writeUint16LE(centralView, 6, 20)
    writeUint16LE(centralView, 8, 0)
    writeUint16LE(centralView, 10, 0)
    writeUint16LE(centralView, 12, 0)
    writeUint16LE(centralView, 14, 0)
    writeUint32LE(centralView, 16, dataCrc)
    writeUint32LE(centralView, 20, dataBytes.length)
    writeUint32LE(centralView, 24, dataBytes.length)
    writeUint16LE(centralView, 28, nameBytes.length)
    writeUint16LE(centralView, 30, 0)
    writeUint16LE(centralView, 32, 0)
    writeUint16LE(centralView, 34, 0)
    writeUint16LE(centralView, 36, 0)
    writeUint32LE(centralView, 38, 0)
    writeUint32LE(centralView, 42, offset)
    centralHeader.set(nameBytes, 46)
    centralParts.push(centralHeader)

    offset += localHeader.length + dataBytes.length
  }

  const centralDirectorySize = centralParts.reduce(
    (total, part) => total + part.length,
    0,
  )
  const endRecord = new Uint8Array(22)
  const endView = new DataView(endRecord.buffer)
  writeUint32LE(endView, 0, 0x06054b50)
  writeUint16LE(endView, 4, 0)
  writeUint16LE(endView, 6, 0)
  writeUint16LE(endView, 8, members.length)
  writeUint16LE(endView, 10, members.length)
  writeUint32LE(endView, 12, centralDirectorySize)
  writeUint32LE(endView, 16, offset)
  writeUint16LE(endView, 20, 0)

  const totalLength =
    localParts.reduce((total, part) => total + part.length, 0) +
    centralDirectorySize +
    endRecord.length
  const archive = new Uint8Array(totalLength)
  let writeOffset = 0
  for (const part of [...localParts, ...centralParts, endRecord]) {
    archive.set(part, writeOffset)
    writeOffset += part.length
  }
  return archive
}
