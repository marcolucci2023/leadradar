from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def hello():
    return {"status": "LeadRadar API is alive!"}

@app.get("/health")
def health():
    return {"ok": True}
