from fastapi import FastAPI

app = FastAPI(
    title="Rueo.ru API",
    description="Новый бэкенд для словаря Rueo.ru",
    version="0.1.0",
)

@app.get("/")
def read_root():
    return {"message": "Hello from Rueo.ru API"}
