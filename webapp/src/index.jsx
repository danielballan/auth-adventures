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
            <p>For Example 3: Basic HTTP, log with username/password</p>
            <input name="username" type="string" required ref={username} />
            <input name="password" type="password" required ref={password} />
            <button onClick={login}>Log in</button>
        </div>
    )
}

const ExternalLogin = () => {
    const search = window.location.search
    const code = new URLSearchParams(search).get("code")

    if (code !== null) {
        axiosClient.get(`/api/code?code=${code}`).then((tokenResponse) => {
            if (tokenResponse.status == 200) {
                localStorage.setItem(
                    "refreshToken",
                    tokenResponse.data.refresh_token
                )
                localStorage.setItem(
                    "accessToken",
                    tokenResponse.data.access_token
                )
                console.log("Login!")
            } else {
                console.log("Login failed")
                console.log(tokenResponse)
            }
        })
    }

    return (
        <div>
            <p>For Example 4: External OIDC, follow this link</p>
            <a href="http://localhost:9000/auth?redirect_uri=http%3A%2F%2Flocalhost%3A8001%2F&client_id=example_client_id&response_type=code&scope=openid">
                Log in with external identity provider
            </a>
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
            <p>Test Authentication By Loading Data:</p>
            <button onClick={loadData}>Load Data</button>
            <button onClick={clearData}>clearData</button>
            {data && <div>Data: {data.toString()}</div>}
        </div>
    )
}

const App = () => (
    <AxiosInterceptor>
        <Login />
        <ExternalLogin />
        <DataLoader />
    </AxiosInterceptor>
)

createRoot(document.getElementById("root")).render(<App />)
