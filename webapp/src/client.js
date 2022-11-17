import axios from "axios"
import { useEffect } from "react"

const axiosClient = axios.create()

const AxiosInterceptor = ({ children }) => {
    useEffect(() => {
        const requestInterceptor = (requestConfig) => {
            // for all requests, lookup refresh token in local storage
            // if found, add to the reqeust
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

        const errInterceptor = (error) => {
            if (error && error.response && (error.response.status === 401)) {
                console.log("needs refresh")
            }
            return Promise.reject(error)
        }

        const reqInterceptor =
            axiosClient.interceptors.request.use(requestInterceptor)
        // const interceptor =
        //     axiosClient.interceptors.response.use(errInterceptor)

        // return () => axiosClient.interceptors.response.eject(interceptor);
    }, [])

    return children
}

export { axiosClient, AxiosInterceptor }
