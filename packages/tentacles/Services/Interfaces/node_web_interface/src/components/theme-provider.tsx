import { createContext, useContext, useEffect } from "react"

type ThemeProviderProps = {
  children: React.ReactNode
  defaultTheme?: string
  storageKey?: string
}

type ThemeProviderState = {
  theme: "dark"
  resolvedTheme: "dark"
  setTheme: (theme: string) => void
}

const ThemeProviderContext = createContext<ThemeProviderState>({
  theme: "dark",
  resolvedTheme: "dark",
  setTheme: () => null,
})

export function ThemeProvider({ children, ...props }: ThemeProviderProps) {
  useEffect(() => {
    document.documentElement.classList.remove("light")
    document.documentElement.classList.add("dark")
  }, [])

  return (
    <ThemeProviderContext.Provider
      value={{ theme: "dark", resolvedTheme: "dark", setTheme: () => null }}
      {...props}
    >
      {children}
    </ThemeProviderContext.Provider>
  )
}

export type Theme = "dark" | "light" | "system"

export const useTheme = () => useContext(ThemeProviderContext)
