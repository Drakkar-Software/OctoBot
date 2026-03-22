import { useMutation, useQuery } from "@tanstack/react-query"
import { useNavigate } from "@tanstack/react-router"

import {
  LoginService,
  type ApiError,
  type User,
  UsersService,
} from "@/client"
import { handleError } from "@/utils"
import useCustomToast from "./useCustomToast"

export type LoginCredentials = {
  username: string
  password: string
}

const isLoggedIn = () => {
  return localStorage.getItem("auth_username") !== null && 
         localStorage.getItem("auth_password") !== null
}

const useAuth = () => {
  const navigate = useNavigate()
  const { showErrorToast } = useCustomToast()

  const { data: user } = useQuery<User | null, Error>({
    queryKey: ["currentUser"],
    queryFn: UsersService.readUserMe,
    enabled: isLoggedIn(),
  })

  const login = async (data: LoginCredentials) => {
    localStorage.setItem("auth_username", data.username)
    localStorage.setItem("auth_password", data.password)
    const user = await LoginService.testAuth()
    // Store the real node address returned by the server
    localStorage.setItem("auth_username", user.email)
  }

  const loginMutation = useMutation({
    mutationFn: login,
    onSuccess: () => {
      navigate({ to: "/" })
    },
    onError: (error) => {
      localStorage.removeItem("auth_password")
      handleError.bind(showErrorToast)(error as ApiError)
    },
  })

  const logout = () => {
    localStorage.removeItem("auth_password")
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
