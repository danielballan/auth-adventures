# Create and read JWT tokens.
# Do not use this! Use jose.jwt or PyJWT instead.

import base64
import hashlib
import hmac
import json
import os
from datetime import datetime

SECRET_KEYS = os.environ["SECRET_KEYS"].split(";")

def base64url_encode(input):
    return base64.urlsafe_b64encode(input).decode("utf-8").replace("=", "")

def base64url_decode(input):
    rem = len(input) % 4
    if rem > 0:
        input += b"=" * (4 - rem)
    return base64.urlsafe_b64decode(input)

def create_jwt(payload):
    # Encode token as JWT:
    # "{base64-encoded header}.{base64-encoded payload}.{signature}"
    header = {"typ": "JWT", "alg": "HS256"}
    segments = [
        base64url_encode(json.dumps(header).encode()),
        base64url_encode(json.dumps(payload).encode()),
    ]
    signing_input = ".".join(segments).encode()
    signing_key = SECRET_KEYS[0].encode()
    signature = hmac.new(signing_key, signing_input, hashlib.sha256).digest()
    segments.append(base64url_encode(signature))
    return ".".join(segments)

def read_jwt(token):
    # Check the header, signature, and expiry. Return the payload or None.
    segments = token.split(".")
    header = json.loads(base64url_decode(segments[0].encode()))
    expected_header = {"typ": "JWT", "alg": "HS256"}
    if header != expected_header:
        print('Unsupported header')
        return None
    payload = json.loads(base64url_decode(segments[1].encode()))
    signature = base64url_decode(segments[2].encode())
    signing_input = ".".join(segments[:2]).encode()
    for key in SECRET_KEYS:
        expected_signature = hmac.new(key.encode(), signing_input, hashlib.sha256).digest()
        if signature == expected_signature:
            break
    else:
        # None of the SECRET_KEYS match.
        print('Invalid signature')
        return None
    if ("exp" in payload) and (payload["exp"] < datetime.now().timestamp()):
        # Token has expired.
        print(f'Token expired at {datetime.fromtimestamp(payload["exp"])}')
        return None
    return payload

