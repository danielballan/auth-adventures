import { useRef, useState } from "react"
import { createRoot } from "react-dom/client"
import { AxiosInterceptor, axiosClient } from "./client"

const Login = () => {
    const username = useRef()
    const password = useRef()

    async function login() {
        const response = await axiosClient.post(
            "/api/login",
            {},
            {
                auth: {
                    username: username.current.value,
                    password: password.current.value
                }
            }
        )
        localStorage.setItem("refreshToken", response.data.refresh_token)
        localStorage.setItem("accessToken", response.data.access_token)
    }

    return (
        <div>
            <input name="username" type="string" required ref={username} />
            <input name="password" type="password" required ref={password} />
            <button onClick={login}>Log in</button>
        </div>
    )
}

const DataLoader = () => {
    const [data, setData] = useState(null)

    async function loadData() {
        const response = await axiosClient.get("/api/data")
        setData(response.data.data)
    }

    const clearData = () => setData(null)

    return (
        <div>
            <button onClick={loadData}>Load Data</button>
            <button onClick={clearData}>clearData</button>
            {data && <div>Data: {data.toString()}</div>}
        </div>
    )
}

const App = () => (
    <AxiosInterceptor>
        <Login />
        <DataLoader />
    </AxiosInterceptor>
)

createRoot(document.getElementById("root")).render(<App />)
