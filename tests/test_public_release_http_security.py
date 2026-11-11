import ast
import sys
import types
from pathlib import Path

import pytest
from fastapi import Depends, FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel


class User:
    def __init__(self, role="member"):
        self.role = role


class SermonRequest(BaseModel):
    topic: str = "Test"


def get_db():
    return None


def get_current_user():
    raise HTTPException(
        status_code=401,
        detail="Not authenticated",
    )


class Query:
    def filter(self, *args):
        return self

    def first(self):
        return None


class Database:
    def query(self, *args):
        return Query()


def load_handler(filename, function_name, namespace):
    source = Path(filename).read_text()
    tree = ast.parse(source)

    matches = [
        node for node in tree.body
        if isinstance(
            node,
            (ast.FunctionDef, ast.AsyncFunctionDef),
        )
        and node.name == function_name
    ]

    assert len(matches) == 1

    node = matches[0]
    node.decorator_list = []

    module = ast.Module(body=[node], type_ignores=[])
    ast.fix_missing_locations(module)

    exec(
        compile(module, filename, "exec"),
        namespace,
    )

    return namespace[function_name]


@pytest.fixture
def app():
    app = FastAPI()

    class Router:
        def post(self, *args, **kwargs):
            return lambda fn: fn

    namespace = {
        "Depends": Depends,
        "HTTPException": HTTPException,
        "Session": Database,
        "User": User,
        "SermonRequest": SermonRequest,
        "get_db": get_db,
        "get_current_user": get_current_user,
        "router": Router(),
        "generate_multiverse_sermons": lambda topic: [],
    }

    admin = load_handler(
        "api/routes/users.py",
        "make_admin",
        namespace,
    )

    multiverse = load_handler(
        "api/routes/faith.py",
        "multiverse_sermons",
        namespace,
    )

    app.post("/users/{user_id}/make-admin")(admin)
    app.post("/api/v1/faith/sermon/multiverse")(
        multiverse
    )

    return app


def test_admin_promotion_rejects_anonymous(app):
    client = TestClient(app)

    response = client.post(
        "/users/1/make-admin"
    )

    assert response.status_code == 401


def test_admin_promotion_rejects_member(app):
    app.dependency_overrides[get_current_user] = (
        lambda: User(role="member")
    )
    app.dependency_overrides[get_db] = (
        lambda: Database()
    )

    client = TestClient(app)

    response = client.post(
        "/users/1/make-admin"
    )

    assert response.status_code == 403


def test_multiverse_rejects_anonymous(app):
    client = TestClient(app)

    response = client.post(
        "/api/v1/faith/sermon/multiverse",
        json={"topic": "Faith"},
    )

    assert response.status_code == 401
