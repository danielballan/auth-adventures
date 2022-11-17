# Adventures in Authentication

This is a series of examples of escalating complexity,
demonstrating authentication schemes with Python servers and clients.
It is not intended for use, only for study.

## Setup

```
git clone https://github.com/danielballan/auth-adventures
pip install -r requirements.txt
```

Run the following examples from the repository root.

## Example 0: No Authentication

```
uvicorn public:app --reload
```

Request `/data`. It succeeds.

```
$ http :8000/data
HTTP/1.1 200 OK
content-length: 16
content-type: application/json
date: Wed, 16 Nov 2022 17:33:10 GMT
server: uvicorn

{
    "data": [
        1,
        2,
        3
    ]
}
```

## Example 1: Single-user API key

```
export API_KEY=secret
uvicorn single_user:app --reload
```

Request `/data`. The server rejects our request with `401 Unauthorized`.

```
$ http :8000/data
HTTP/1.1 401 Unauthorized
content-length: 15
content-type: application/json
date: Wed, 16 Nov 2022 20:32:43 GMT
server: uvicorn

{
    "error": "..."
}
```

Do that again showing the headers in our request.

```
$ http -phHb :8000/data
GET /data HTTP/1.1
Accept: */*
Accept-Encoding: gzip, deflate
Connection: keep-alive
Host: localhost:8000
User-Agent: HTTPie/1.0.3

HTTP/1.1 401 Unauthorized
content-length: 15
content-type: application/json
date: Wed, 16 Nov 2022 17:43:15 GMT
server: uvicorn

{
    "error": "..."
}
```

Add a header like `Authorization:Apikey {API key}`

```
$ http -phHb :8000/data 'Authorization:Apikey secret'
GET /data HTTP/1.1
Accept: */*
Accept-Encoding: gzip, deflate
Authorization: Apikey secret
Connection: keep-alive
Host: localhost:8000
User-Agent: HTTPie/1.0.3

HTTP/1.1 200 OK
content-length: 16
content-type: application/json
date: Wed, 16 Nov 2022 20:43:45 GMT
server: uvicorn

{
    "data": [
        1,
        2,
        3
    ]
}
```

Add a query parameter `api_key={API key}`.

```
$ http -phHb :8000/data?api_key=secret
GET /data?api_key=secret HTTP/1.1
Accept: */*
Accept-Encoding: gzip, deflate
Connection: keep-alive
Host: localhost:8000
User-Agent: HTTPie/1.0.3

HTTP/1.1 200 OK
content-length: 16
content-type: application/json
date: Wed, 16 Nov 2022 20:44:27 GMT
server: uvicorn

{
    "data": [
        1,
        2,
        3
    ]
}
```

## Example 2: HTTP Basic (on every request)

```
export SECRET_KEYS=secret
uvicorn http_basic:app --reload
```

Request `/data`. The server rejects our request with `401 Unauthorized`.

```
$ http :8000/data
HTTP/1.1 401 Unauthorized
content-length: 15
content-type: application/json
date: Wed, 16 Nov 2022 17:42:03 GMT
server: uvicorn

{
    "error": "..."
}
```

Do that again showing the headers in our request.

```
$ http -phHb :8000/data
GET /data HTTP/1.1
Accept: */*
Accept-Encoding: gzip, deflate
Connection: keep-alive
Host: localhost:8000
User-Agent: HTTPie/1.0.3

HTTP/1.1 401 Unauthorized
content-length: 15
content-type: application/json
date: Wed, 16 Nov 2022 17:43:15 GMT
server: uvicorn

{
    "error": "..."
}
```

Provide credentials via "HTTP basic".

```
$ http -phHb :8000/data --auth dallan:password
GET /data HTTP/1.1
Accept: */*
Accept-Encoding: gzip, deflate
Authorization: Basic ZGFsbGFuOnBhc3N3b3Jk
Connection: keep-alive
Host: localhost:8000
User-Agent: HTTPie/1.0.3

HTTP/1.1 200 OK
content-length: 36
content-type: application/json
date: Wed, 16 Nov 2022 17:44:54 GMT
server: uvicorn

{
    "data": [
        1,
        2,
        3
    ],
    "who_am_i": "dallan"
}
```

The string `dallan:password` was base64-encoded and placed in the
`Authorization` header like
`Authorization: Basic {base64-encoded username:password}`.

If we send the wrong password, the request is, correctly, rejected.

```
$ http -phHb :8000/data --auth dallan:wrong_password
GET /data HTTP/1.1
Accept: */*
Accept-Encoding: gzip, deflate
Authorization: Basic ZGFsbGFuOndyb25nX3Bhc3N3b3Jk
Connection: keep-alive
Host: localhost:8000
User-Agent: HTTPie/1.0.3

HTTP/1.1 401 Unauthorized
content-length: 15
content-type: application/json
date: Wed, 16 Nov 2022 17:48:21 GMT
server: uvicorn

{
    "error": "..."
}
```

Notice that we have to send our credentials on every request.
This means that our client program has to keep them or else
force us to re-enter them.

```
In [1]: from httpx import Client

In [2]: client = Client(base_url="http://localhost:8000")

In [3]: client.get("/data")
Out[3]: <Response [401 Unauthorized]>

In [4]: client.get("/data", auth=("dallan", "password"))
Out[4]: <Response [200 OK]>

In [5]: client.auth = ("dallan", "password")

In [6]: client.get("/data")
Out[6]: <Response [200 OK]>

In [7]: client.get("/data").json()
Out[7]: {'data': [1, 2, 3], 'who_am_i': 'dallan'}
```

## Example 3: HTTP Basic into OAuth2

```
export SECRET_KEYS=secret
uvicorn http_basic:app --reload
```

```
$ http POST :8000/login --auth dallan:password
HTTP/1.1 200 OK
content-length: 354
content-type: application/json
date: Wed, 16 Nov 2022 18:00:23 GMT
server: uvicorn

{
    "access_token": "eyJ0eXAiOiAiSldUIiwgImFsZyI6ICJIUzI1NiJ9.eyJzdWIiOiAiZGFsbGFuIiwgInR5cGUiOiAiYWNjZXNzIiwgImV4cCI6IDE2Njg2MjE2MzR9.9ZxERUD-ip294gQQn_iOzcsaslfWz1Y0l5rzYidR7Kw",
    "refresh_token": "eyJ0eXAiOiAiSldUIiwgImFsZyI6ICJIUzI1NiJ9.eyJzdWIiOiAiZGFsbGFuIiwgInR5cGUiOiAicmVmcmVzaCIsICJleHAiOiAxNjY5ODMxMjI0fQ.lg-lkB0lUMhB4150i0u6EEAofnRW4KZBeRzUAZZAGrw"
}
```

Log in again, this time stashing the response body to a file.

```
$ http POST :8000/login --auth dallan:password > tokens.json
$ jq . < tokens.json
{
  "refresh_token": "eyJ0eXAiOiAiSldUIiwgImFsZyI6ICJIUzI1NiJ9.eyJzdWIiOiAiZGFsbGFuIiwgInR5cGUiOiAicmVmcmVzaCIsICJleHAiOiAxNjY5ODMxMjQwfQ.Un9hUs-xS64nqc-aOjM4QeaeCkJs-55OPtch4NE6a_Y",
  "access_token": "eyJ0eXAiOiAiSldUIiwgImFsZyI6ICJIUzI1NiJ9.eyJzdWIiOiAiZGFsbGFuIiwgInR5cGUiOiAiYWNjZXNzIiwgImV4cCI6IDE2Njg2MjE2NTB9.aCtlXCYRBIZpaqgRf_bI0RVwSvOBx_Ul6vvKtWhqm1Y"
}
```

Extract the access token to construct a header like `Authorization: Bearer {access_token}`.

```
$ http -pHhb :8000/data "Authorization:Bearer $(jq -r '.access_token' < tokens.json)"
GET /data HTTP/1.1
Accept: */*
Accept-Encoding: gzip, deflate
Authorization: Bearer eyJ0eXAiOiAiSldUIiwgImFsZyI6ICJIUzI1NiJ9.eyJzdWIiOiAiZGFsbGFuIiwgInR5cGUiOiAiYWNjZXNzIiwgImV4cCI6IDE2Njg2MjIxMzJ9.Fm14DLBFf1_OFaSvdTzSoBBeeBrWpQb2BO3kA-pgwJc
Connection: keep-alive
Host: localhost:8000
User-Agent: HTTPie/1.0.3

HTTP/1.1 200 OK
content-length: 36
content-type: application/json
date: Wed, 16 Nov 2022 18:08:42 GMT
server: uvicorn

{
    "data": [
        1,
        2,
        3
    ],
    "who_am_i": "dallan"
}
```

When the access token expires, exchange the refresh token for a new pair of tokens.

```
$ http POST :8000/refresh <<< $(jq -r . < tokens.json) > tokens.json
```

The `httpx` client enables us to implement this refresh flow using a coroutine.

```
$ python client_refresh_flow.py
Username: dallan
Password: password
<Response [200 OK]>
<Response [200 OK]>
<Response [200 OK]>
<Response [200 OK]>
<Response [200 OK]>
<Response [200 OK]>
...
```

Watching the server logs while this runs:

```
INFO:     127.0.0.1:35098 - "POST /login HTTP/1.1" 200 OK
INFO:     127.0.0.1:35098 - "GET /data HTTP/1.1" 200 OK
INFO:     127.0.0.1:35098 - "GET /data HTTP/1.1" 200 OK
INFO:     127.0.0.1:35098 - "GET /data HTTP/1.1" 200 OK
INFO:     127.0.0.1:35098 - "GET /data HTTP/1.1" 200 OK
INFO:     127.0.0.1:35098 - "GET /data HTTP/1.1" 200 OK
Token expired at 2022-11-16 16:11:24
INFO:     127.0.0.1:35098 - "GET /data HTTP/1.1" 401 Unauthorized
INFO:     127.0.0.1:35098 - "POST /refresh HTTP/1.1" 200 OK
INFO:     127.0.0.1:35098 - "GET /data HTTP/1.1" 200 OK
INFO:     127.0.0.1:35098 - "GET /data HTTP/1.1" 200 OK
INFO:     127.0.0.1:35098 - "GET /data HTTP/1.1" 200 OK
INFO:     127.0.0.1:35098 - "GET /data HTTP/1.1" 200 OK
```

we see that the access token periodicially expires and a new one is obtained.
This exchange happens transpently to the user, who sees only the success requests
after the failing ones are retried.

## Example 4: External OIDC into OAuth2 Device Code Flow

Start an OIDC provider using the Docker image
[qlik/simple-oidc-provider](https://hub.docker.com/r/qlik/simple-oidc-provider/).
This will stand in for an external identity provider like Google, Globus, ORCID,
GitHub, etc.

```
docker run --rm -p 9000:9000 -v $(pwd):/config -e CONFIG_FILE=/config/oidc_provider_config.json -e USERS_FILE=/config/users.json qlik/simple-oidc-provider:0.2.4
```

Note: The version of the Docker image is intentionally tagged `0.2.4`. The `latest` tag
does not work; the failure seems to be related to an experimental feature in that version.

```
export SECRET_KEYS=secret
uvicorn external_oidc_into_oauth2:app --reload
```

Note: At startup, the `example_oidc_into_oauth2` server downlaods some information from the OIDC provider. It must be started after the OIDC provider, and if the OIDC provider is ever restarted, the server must be restarted too.

```
$ http POST :8000/authorize > info.json
$ jq . < info.json
{
  "authorization_uri": "http://localhost:9000/auth?client_id=example_client_id&response_type=code&scope=openid&redirect_uri=http%3A%2F%2Flocalhost%3A8000%2Fdevice_code_callback",
  "verification_uri": "http://localhost:8000/token",
  "interval": 2,
  "device_code": "3dc36914977264d501e1a60f29cf626c2f4cadee8e290e5385b4f38c1ef64543",
  "expires_in": 900,
  "user_code": "47C68550"
}
```

The server logs show that a `PendingSession` was created.

```
Created PendingSession(user_code='A2E403CA', device_code='6fd0ee106c2ba246d98b65e43fe7f4caa5edf9426651743551d05b9c0b98fb3d', deadline=datetime.datetime(2022, 11, 16, 21, 33, 18, 467853), username=None)
```

Navigate a browser to `authorization_uri`.

```
$ xdg-open $(jq -r .authorization_uri < info.json)
```

Log in with `dallan@example.com` and `password`. When prompted "Enter code", enter the `user_code` from `info.json`. You should see a confirmation message in the browser.

The pending session is now verified, as the server logs show.

```
Verified PendingSession(user_code='A2E403CA', device_code='6fd0ee106c2ba246d98b65e43fe7f4caa5edf9426651743551d05b9c0b98fb3d', deadline=datetime.datetime(2022, 11, 16, 21, 33, 18, 467853), username='dallan')
```

Collect the tokens. This can only be done once.

```
$ http --form POST :8000/token "device_code=$(jq -r '.device_code' < info.json)" > tokens.json
$ jq . < tokens.json
{
  "refresh_token": "eyJ0eXAiOiAiSldUIiwgImFsZyI6ICJIUzI1NiJ9.eyJzdWIiOiAiZGFsbGFuIiwgInR5cGUiOiAicmVmcmVzaCIsICJleHAiOiAxNjY5ODYwMzI1fQ.43-h1tgz1ZeFay9fO6N7avh-12Yx5TNr8uLr87d0w9k",
  "access_token": "eyJ0eXAiOiAiSldUIiwgImFsZyI6ICJIUzI1NiJ9.eyJzdWIiOiAiZGFsbGFuIiwgInR5cGUiOiAiYWNjZXNzIiwgImV4cCI6IDE2Njg2NTA3MzV9.bM8LXqaVtamakcJDPZ5taJlWylramFl3PKbmRwDvp-s"
}
```

The server logs confirm that the lifecycle of this PendingSession is complete.

```
Used PendingSession(user_code='A2E403CA', device_code='6fd0ee106c2ba246d98b65e43fe7f4caa5edf9426651743551d05b9c0b98fb3d', deadline=datetime.datetime(2022, 11, 16, 21, 33, 18, 467853), username='dallan')
```

And now access and refresh work as in Example 3:

```
$ http POST :8000/refresh <<< $(jq -r . < tokens.json) > tokens.json
$ http -pHhb :8000/data "Authorization:Bearer $(jq -r '.access_token' < tokens.json)"
GET /data HTTP/1.1
Accept: */*
Accept-Encoding: gzip, deflate
Authorization: Bearer eyJ0eXAiOiAiSldUIiwgImFsZyI6ICJIUzI1NiJ9.eyJzdWIiOiAiZGFsbGFuIiwgInR5cGUiOiAiYWNjZXNzIiwgImV4cCI6IDE2Njg2NTA4MzZ9.trYhD8yHW7cvK4_JagnUziu2KtqzAdjci65jXf0kxY4
Connection: keep-alive
Host: localhost:8000
User-Agent: HTTPie/1.0.3

HTTP/1.1 200 OK
content-length: 36
content-type: application/json
date: Thu, 17 Nov 2022 02:07:14 GMT
server: uvicorn

{
    "data": [
        1,
        2,
        3
    ],
    "who_am_i": "dallan"
}
```

Run the whole process again from Python:

```
python client_device_code_flow.py
You have 900 seconds to enter the code

    204A18A4

after authorizing at the URL:

    http://localhost:9000/auth?client_id=example_client_id&response_type=code&scope=openid&redirect_uri=http%3A%2F%2Flocalhost%3A8000%2Fdevice_code_callback

Waiting........
Logged in!
<Response [200 OK]>
{'data': [1, 2, 3], 'who_am_i': 'dallan'}
```
