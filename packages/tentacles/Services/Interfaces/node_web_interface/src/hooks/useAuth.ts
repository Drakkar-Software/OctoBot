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
    // Store credentials for Basic Auth
    localStorage.setItem("auth_username", data.username)
    localStorage.setItem("auth_password", data.password)
    
    // Test authentication by calling the test endpoint
    await LoginService.testAuth()
  }

  const loginMutation = useMutation({
    mutationFn: login,
    onSuccess: () => {
      navigate({ to: "/" })
    },
    onError: (error) => {
      // Clear credentials on error
      localStorage.removeItem("auth_username")
      localStorage.removeItem("auth_password")
      handleError.bind(showErrorToast)(error as ApiError)
    },
  })

  const logout = () => {
    localStorage.removeItem("auth_username")
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
