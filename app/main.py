from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import engine, Base
from .routers import auth, cases, admin, gp, qa

# Create Tables automatically (if they don't exist)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="GP QA Case Flow Demo")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For production, change "*" to your Vercel URL later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the routers
app.include_router(auth.router)
app.include_router(cases.router)
app.include_router(admin.router)
app.include_router(gp.router)
app.include_router(qa.router)

@app.get("/")
def root():
    return {"message": "System is running"}