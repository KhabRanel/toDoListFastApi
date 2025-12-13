const api = "http://127.0.0.1:8000";

async function loadTasks() {
  const res = await fetch(`${api}/tasks?sort=created_at&order=desc`);
  const tasks = await res.json();
  const list = document.getElementById("taskList");
  list.innerHTML = "";

  tasks.forEach(t => {
    const li = document.createElement("li");
    li.innerHTML = `
      <strong>${t.title}</strong>
      [приоритет: ${t.priority}]
      ${t.is_done ? "✅" : ""}
      <button onclick="toggleDone(${t.id}, ${t.is_done})">
        ${t.is_done ? "Отменить" : "Готово"}
      </button>
      <button onclick="deleteTask(${t.id})">Удалить</button>
    `;
    list.appendChild(li);
  });
}

async function addTask(e) {
  e.preventDefault();
  const title = document.getElementById("title").value.trim();
  const priority = parseInt(document.getElementById("priority").value);
  const res = await fetch(`${api}/tasks`, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({ title, priority })
  });
  if (res.ok) {
    document.getElementById("title").value = "";
    await loadTasks();
  } else {
    alert("Ошибка при добавлении задачи");
  }
}

async function toggleDone(id, done) {
  await fetch(`${api}/tasks/${id}`, {
    method: "PUT",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({ is_done: !done })
  });
  await loadTasks();
}

async function deleteTask(id) {
  await fetch(`${api}/tasks/${id}`, { method: "DELETE" });
  await loadTasks();
}

document.getElementById("taskForm").addEventListener("submit", addTask);
loadTasks();
