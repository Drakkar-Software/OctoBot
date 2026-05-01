import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { useNavigate } from "@tanstack/react-router"

import { type ApiError, LoginService, type User, UsersService } from "@/client"
import { clearPassword, savePassword } from "@/lib/device-key"

export const clearAuth = async () => {
  localStorage.removeItem("auth_username")
  localStorage.removeItem("auth_wallet_name")
  await clearPassword()
}

import { handleError } from "@/utils"
import useCustomToast from "./useCustomToast"

export type LoginCredentials = {
  username: string
  password: string
}

const isLoggedIn = () => {
  return localStorage.getItem("auth_username") !== null
}

const useAuth = () => {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { showErrorToast } = useCustomToast()

  const { data: user } = useQuery<User | null, Error>({
    queryKey: ["currentUser"],
    queryFn: UsersService.readUserMe,
    enabled: isLoggedIn(),
  })

  const login = async (data: LoginCredentials) => {
    localStorage.setItem("auth_username", data.username)
    await savePassword(data.password)
    try {
      const loggedInUser = await LoginService.testAuth()
      // Store the real node address returned by the server
      localStorage.setItem("auth_username", loggedInUser.email)
      // Store wallet display name for header/menu
      if (loggedInUser.full_name) {
        localStorage.setItem("auth_wallet_name", loggedInUser.full_name)
      } else {
        localStorage.removeItem("auth_wallet_name")
      }
    } catch (err) {
      // Clean up before propagating so isLoggedIn() never returns true for failed logins
      await clearAuth()
      throw err
    }
  }

  const loginMutation = useMutation({
    mutationFn: login,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["currentUser"] })
      navigate({ to: "/" })
    },
    onError: (error) => {
      // clearAuth() already called inside login() before re-throwing
      handleError.bind(showErrorToast)(error as ApiError)
    },
  })

  const logout = async () => {
    await clearAuth()
    navigate({ to: "/login" })
  }

  return {
    loginMutation,
    logout,
    user,
  }
}

export { isLoggedIn }
export default useAuth
