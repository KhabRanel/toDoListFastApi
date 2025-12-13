# TODO FastAPI — Лабораторная работа №7

## Сборка Docker образа

docker build -t todo-fastapi .

## Запуск проекта в Docker

docker compose up --build

## Запуск тестов
docker run todo-fastapi pytest
