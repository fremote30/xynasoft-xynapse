from fastapi import HTTPException, Request


def require_role(role):

    def role_checker(request: Request):

        user = request.state.user

        if not user:
            raise HTTPException(status_code=401)

        if user["role"] != role:
            raise HTTPException(status_code=403)

        return user

    return role_checker