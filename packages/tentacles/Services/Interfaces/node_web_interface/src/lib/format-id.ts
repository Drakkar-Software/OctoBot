const ID_DISPLAY_LENGTH = 8

export function formatIdDisplay(id: string): string {
  if (id.length <= ID_DISPLAY_LENGTH) return id
  return id.slice(0, ID_DISPLAY_LENGTH)
}
