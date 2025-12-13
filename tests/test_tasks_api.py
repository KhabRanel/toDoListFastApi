import pytest
from httpx import AsyncClient
from app.app_main import app, Base, engine

# --- фикстура для чистой базы ---
@pytest.fixture(autouse=True)
def clear_db():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield


@pytest.mark.asyncio
async def test_health():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        resp = await ac.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_create_task_success():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        data = {
            "title": "Test task",
            "priority": 2,
            "due_date": "2025-12-31T23:59:59"
        }
        resp = await ac.post("/tasks", json=data)
        assert resp.status_code == 201
        body = resp.json()
        assert body["title"] == "Test task"
        assert body["priority"] == 2
        assert "id" in body


@pytest.mark.asyncio
async def test_create_task_invalid_priority():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        data = {"title": "Bad", "priority": 10}
        resp = await ac.post("/tasks", json=data)
        assert resp.status_code == 422


@pytest.mark.asyncio
async def test_list_tasks_filter_and_sort():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # Создадим три задачи
        await ac.post("/tasks", json={"title": "A", "priority": 1})
        await ac.post("/tasks", json={"title": "B", "priority": 3})
        await ac.post("/tasks", json={"title": "C", "priority": 2})

        # Сортировка по priority desc
        resp = await ac.get("/tasks?sort=priority&order=desc")
        body = resp.json()

        pr_list = [task["priority"] for task in body]
        assert pr_list == sorted(pr_list, reverse=True)


@pytest.mark.asyncio
async def test_get_task_not_found():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        resp = await ac.get("/tasks/999")
        assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_task():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # создаём
        resp = await ac.post("/tasks", json={"title": "Old"})
        tid = resp.json()["id"]

        # обновляем
        resp2 = await ac.put(f"/tasks/{tid}", json={"is_done": True})
        assert resp2.status_code == 200
        assert resp2.json()["is_done"] is True


@pytest.mark.asyncio
async def test_delete_task():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        resp = await ac.post("/tasks", json={"title": "Delete me"})
        tid = resp.json()["id"]

        resp2 = await ac.delete(f"/tasks/{tid}")
        assert resp2.status_code == 204

        resp3 = await ac.get(f"/tasks/{tid}")
        assert resp3.status_code == 404
