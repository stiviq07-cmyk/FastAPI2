from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn
import sqlite3
from fastapi import HTTPException
from typing import Optional, List
from fastapi.responses import HTMLResponse


app = FastAPI(title="NoteAPI")

DB_PATH = "notes.db"

#подключение к базе данных
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor() #создает курсор


    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            is_public BOOLEAN NOT NULL DEFAULT 0
        )
    """)

    conn.commit()
    conn.close()

#запуск создания БД при старте, если база уже существует ничего не произойдет
init_db()

#функция для подключения к базе, используется во всех запросах
def get_db():
    conn = sqlite3.connect(DB_PATH) #соединение с базой данных
    conn.row_factory = sqlite3.Row  #чтобы обращаться к данным по именам колонок (например row["title"])
    return conn #возвращает подключение к базе



#создаем таблицу при запуске приложения
def create_table():
    print("table created")

create_table()


# ---------------------------------------
#модели Pydantic для валидации данных
class NoteCreate(BaseModel):
#модель для создания заметки
    title: str
    content: str

#модель для обновления заметки
class NoteUpdate(BaseModel):
    title: Optional[str] = None #может быть строкой или ничего
    content: Optional[str] = None

#модель заметки с id
class Note(NoteCreate):
    id: int #добавляет поле айди


#функции для работы с базой данных
def read_data():
#чтение всех заметок из базы данных
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, content FROM notes ORDER BY id") #скл запрос
    rows = cursor.fetchall() #получим все строки таблицы
    conn.close()
    return [dict(row) for row in rows] #проеобразует данные в списор словарей


def write_data(data): #полная перезапись всех заметок в базе данных
    conn = get_db()
    cursor = conn.cursor()

#очищим таблицу
    cursor.execute("DELETE FROM notes")

#вставляем все заметки заново
    for note in data:
        cursor.execute(
            "INSERT INTO notes (title, content) VALUES (?, ?)",
            (note["title"], note["content"])
        )

    conn.commit()
    conn.close()


# ---------------------------------------


#GET — проверить, что сервер работает
@app.get("/") #создает маршрут
def root():
    return {"message": "Сервер работает"} #возращает джсон


#GET — получить все заметки
@app.get("/notes", response_model=List[Note]) #получет заметки, адрес
def get_notes():
#солучить список всех заметок
    notes = read_data()
    return notes


#POST — создать новую заметку
@app.post("/notes", response_model=Note)
def create_note(note: NoteCreate):
#создать новую заметку
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO notes (title, content) VALUES (?, ?)",
        (note.title, note.content)
    )

    conn.commit()

#получим созданную заметку
    note_id = cursor.lastrowid
    cursor.execute("SELECT id, title, content FROM notes WHERE id = ?", (note_id,))
    new_note = dict(cursor.fetchone())

    conn.close()
    return new_note


#GET — получить конкретную заметку по ID
@app.get("/notes/{note_id}", response_model=Note)
def get_note(note_id: int):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT id, title, content FROM notes WHERE id = ?", (note_id,))
    note = cursor.fetchone()
    conn.close()

    if note is None:
        raise HTTPException(status_code=404, detail="Заметка не найдена")

    return dict(note)


#PUT - полностью обновить заметку
@app.put("/notes/{note_id}", response_model=Note)
def update_note(note_id: int, note: NoteCreate):
#полностью обновить заметку
    conn = get_db()
    cursor = conn.cursor()

#проверим существование заметки
    cursor.execute("SELECT id FROM notes WHERE id = ?", (note_id,))
    if cursor.fetchone() is None:
        conn.close()
        raise HTTPException(status_code=404, detail="Заметка не найдена")

#пбновим заметку
    cursor.execute(
        "UPDATE notes SET title = ?, content = ? WHERE id = ?",
        (note.title, note.content, note_id)
    )

    conn.commit()

#получим обновленную заметку
    cursor.execute("SELECT id, title, content FROM notes WHERE id = ?", (note_id,))
    updated_note = dict(cursor.
                        fetchone())
    conn.close()

    return updated_note


#PATCH - частично обновить заметку
@app.patch("/notes/{note_id}", response_model=Note)
def patch_note(note_id: int, note: NoteUpdate):
#частично обновить заметку
    conn = get_db()
    cursor = conn.cursor()

#проверим существование заметки и получим текущие данные
    cursor.execute("SELECT title, content FROM notes WHERE id = ?", (note_id,))
    current = cursor.fetchone()

    if current is None:
        conn.close()
        raise HTTPException(status_code=404, detail="Заметка не найдена")

#обновим только переданные поля
    new_title = note.title if note.title is not None else current["title"]
    new_content = note.content if note.content is not None else current["content"]

    cursor.execute(
        "UPDATE notes SET title = ?, content = ? WHERE id = ?",
        (new_title, new_content, note_id)
    )

    conn.commit()

#получим обновленную заметку
    cursor.execute("SELECT id, title, content FROM notes WHERE id = ?", (note_id,))
    updated_note = dict(cursor.fetchone())
    conn.close()

    return updated_note


#DELETE - удалить заметку
@app.delete("/notes/{note_id}")
def delete_note(note_id: int):
#удалить заметку по ID
    conn = get_db()
    cursor = conn.cursor()

#проверим существование заметки
    cursor.execute("SELECT id FROM notes WHERE id = ?", (note_id,))
    if cursor.fetchone() is None:
        conn.close()
        raise HTTPException(status_code=404, detail="Заметка не найдена")

#удалим заметку
    cursor.execute("DELETE FROM notes WHERE id = ?", (note_id,))
    conn.commit()
    conn.close()

    return {"message": "Заметка успешно удалена"}


# ---------------------------------------


if __name__ == "__main__":
    uvicorn.run("main:app", reload=True)

