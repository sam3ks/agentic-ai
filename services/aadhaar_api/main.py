from fastapi import FastAPI
from app.routes import router, initialize_database
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Aadhaar Microservice")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

initialize_database()
