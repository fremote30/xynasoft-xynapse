from fastapi import Request
from jose import jwt
from api.core.config import settings


async def auth_middleware(request: Request, call_next):

    token = request.headers.get("Authorization")

    if token:

        try:

            token = token.replace("Bearer ", "")

            payload = jwt.decode(
                token,
                settings.JWT_SECRET,
                algorithms=["HS256"]
            )

            request.state.user = payload

        except:
            request.state.user = None

    response = await call_next(request)

    return response