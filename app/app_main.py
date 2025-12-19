from fastapi import FastAPI, HTTPException, Query, Path, status
from typing import Optional, List, Dict, Any
from sqlalchemy import create_engine, select
from sqlalchemy.orm import declarative_base, mapped_column, Mapped, Session
from sqlalchemy.types import Integer, String
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
from pydantic import BaseModel, Field
import datetime


class TaskCreate(BaseModel):
    title: str = Field(..., min_length=3)
    details: Optional[str] = None
    is_done: Optional[bool] = False
    priority: Optional[int] = Field(1, ge=1, le=3)
    due_date: Optional[str] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=3)
    details: Optional[str] = None
    is_done: Optional[bool] = None
    priority: Optional[int] = Field(None, ge=1, le=3)
    due_date: Optional[str] = None


class TaskResponse(BaseModel):
    id: int
    title: str
    details: Optional[str]
    is_done: bool
    priority: int
    due_date: Optional[str]
    created_at: str
    updated_at: Optional[str]

    class Config:
        from_attributes = True


# --- Настройки БД ---
DATABASE_URL = "sqlite:///./lab.db"
engine = create_engine(DATABASE_URL, echo=False, future=True)
Base = declarative_base()

# --- ORM-модель ---
class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    details: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    is_done: Mapped[int] = mapped_column(Integer, default=0)
    priority: Mapped[int] = mapped_column(Integer, default=1)
    due_date: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[str] = mapped_column(String, nullable=False)
    updated_at: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "details": self.details,
            "is_done": bool(self.is_done),
            "priority": self.priority,
            "due_date": self.due_date,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

# --- Создание таблицы ---
Base.metadata.create_all(engine)

# --- Приложение ---
app = FastAPI(title="TODO API (FastAPI + ORM)")


# --- Валидация данных ---
def validate_task(data: Dict[str, Any]):
    if not isinstance(data, dict):
        raise HTTPException(400, "Body must be JSON")

    # title
    if "title" not in data or not isinstance(data["title"], str) or len(data["title"].strip()) < 3:
        raise HTTPException(400, "Invalid or missing 'title'")

    # is_done
    if "is_done" in data:
        if not isinstance(data["is_done"], (bool, int)):
            raise HTTPException(400, "'is_done' must be boolean")
        data["is_done"] = int(bool(data["is_done"]))
    else:
        data["is_done"] = 0

    # due_date
    if "due_date" in data and data["due_date"] is not None:
        if not isinstance(data["due_date"], str):
            raise HTTPException(400, "'due_date' must be a string in ISO format")
        try:
            datetime.datetime.fromisoformat(data["due_date"])
        except Exception:
            raise HTTPException(400, "Invalid ISO date format in 'due_date'")

    # details
    if "details" in data and data["details"] is not None and not isinstance(data["details"], str):
        raise HTTPException(400, "'details' must be a string")

# --- Эндпоинты ---
@app.get("/health", tags=["system"])
def health():
    return {"status": "ok"}

# Список задач
@app.get("/tasks", response_model=list[TaskResponse])
def list_tasks(
    q: Optional[str] = Query(None),
    is_done: Optional[bool] = Query(None),
    priority: Optional[int] = Query(None),
    due_before: Optional[str] = Query(None),
    due_after: Optional[str] = Query(None),
    sort: Optional[str] = Query("created_at"),
    order: Optional[str] = Query("asc"),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    valid_sort_fields = ["created_at", "due_date", "priority"]
    if sort not in valid_sort_fields:
        raise HTTPException(400, f"Invalid sort field '{sort}'")
    if order.lower() not in ["asc", "desc"]:
        raise HTTPException(400, f"Invalid order '{order}'")

    with Session(engine) as session:
        stmt = select(Task)

        # фильтры
        if q:
            ql = f"%{q.lower()}%"
            stmt = stmt.where((Task.title.ilike(ql)) | (Task.details.ilike(ql)))
        if is_done is not None:
            stmt = stmt.where(Task.is_done == (1 if is_done else 0))
        if priority:
            stmt = stmt.where(Task.priority == priority)
        if due_before:
            stmt = stmt.where(Task.due_date <= due_before)
        if due_after:
            stmt = stmt.where(Task.due_date >= due_after)

        # сортировка
        col = getattr(Task, sort)
        stmt = stmt.order_by(col.desc() if order.lower() == "desc" else col.asc())

        # пагинация
        stmt = stmt.offset(offset).limit(limit)
        tasks = session.scalars(stmt).all()
        return [t.to_dict() for t in tasks]

# Получить задачу
@app.get("/tasks/{task_id}", response_model=TaskResponse)
def get_task(task_id: int = Path(ge=1)):
    with Session(engine) as session:
        obj = session.get(Task, task_id)
        if not obj:
            raise HTTPException(404, "Task not found")
        return obj

# Создать задачу
@app.post("/tasks", response_model=TaskResponse, status_code=201)
def create_task(payload: TaskCreate):
    data = payload.dict()
    validate_task(data)

    now = datetime.datetime.now().isoformat()

    obj = Task(
        title=data["title"],
        details=data.get("details"),
        is_done=int(data.get("is_done", False)),
        priority=data.get("priority", 1),
        due_date=data.get("due_date"),
        created_at=now,
        updated_at=None,
    )

    with Session(engine) as session:
        session.add(obj)
        session.commit()
        session.refresh(obj)
        return obj


# Обновить задачу
@app.put("/tasks/{task_id}", response_model=TaskResponse)
def update_task(task_id: int, payload: TaskUpdate):
    with Session(engine) as session:
        obj = session.get(Task, task_id)
        if not obj:
            raise HTTPException(404, "Task not found")

        data = payload.dict(exclude_unset=True)

        if "title" in data:
            obj.title = data["title"]
        if "details" in data:
            obj.details = data["details"]
        if "is_done" in data:
            obj.is_done = int(bool(data["is_done"]))
        if "priority" in data:
            obj.priority = data["priority"]
        if "due_date" in data:
            obj.due_date = data["due_date"]

        obj.updated_at = datetime.datetime.now().isoformat()

        session.commit()
        session.refresh(obj)
        return obj


# Удалить задачу
@app.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: int):
    with Session(engine) as session:
        obj = session.get(Task, task_id)
        if not obj:
            raise HTTPException(404, "Task not found")
        session.delete(obj)
        session.commit()


# --- Подключаем статические файлы ---
current_dir = os.path.dirname(__file__)
static_dir = os.path.join(current_dir, "static")

app.mount("/static", StaticFiles(directory=static_dir), name="static")

# --- Главная страница ---
@app.get("/", response_class=FileResponse, tags=["frontend"])
def index():
    return FileResponse(os.path.join(static_dir, "index.html"))

