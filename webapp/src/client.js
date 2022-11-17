import axios from "axios"
import { useEffect } from "react"

const axiosClient = axios.create()

const AxiosInterceptor = ({ children }) => {
    useEffect(() => {
        const requestInterceptor = (requestConfig) => {
            const storedAccessToken = localStorage.getItem("accessToken")
            if (storedAccessToken) {
                if (!requestConfig.headers) {
                    requestConfig.headers = {}
                }
                requestConfig.headers["Authorization"] =
                    "Bearer " + storedAccessToken
            }
            return requestConfig
        }

        const requestErrorInterceptor = (error) => {
            return Promise.reject(error)
        }

        const responseInterceptor = (response) => {
            return response
        }
        const responseErrorInterceptor = (error) => {
            if (error.response && error.response.status == 401) {
                localStorage.removeItem("accessToken")
                console.log("Attempting refresh")
                const storedRefreshToken = localStorage.getItem("refreshToken")
                axiosClient
                    .post("/api/refresh", {
                        refresh_token: storedRefreshToken
                    })
                    .then((tokenResponse) => {
                        if (tokenResponse.status == 200) {
                            localStorage.setItem(
                                "refreshToken",
                                tokenResponse.data.refresh_token
                            )
                            localStorage.setItem(
                                "accessToken",
                                tokenResponse.data.access_token
                            )
                            console.log("Refresh successful")
                            return axiosClient(error.config)
                        } else {
                            console.log("Refresh failed")
                        }
                    })
            } else {
                console.log("response error")
            }
            return Promise.reject(error)
        }

        const reqInterceptor = axiosClient.interceptors.request.use(
            requestInterceptor,
            requestErrorInterceptor
        )
        const resInterceptor = axiosClient.interceptors.response.use(
            responseInterceptor,
            responseErrorInterceptor
        )

        // return () => axiosClient.interceptors.response.eject(interceptor);
    }, [])

    return children
}

export { axiosClient, AxiosInterceptor }
