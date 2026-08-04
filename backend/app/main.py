"""Entry point của FastAPI app: khởi tạo app, middleware và include các router."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.routers import ai_agent, auth, cart, chat, orders, products, reviews

settings = get_settings()

app = FastAPI(title=settings.APP_NAME)

# TODO: giới hạn allow_origins về domain thật của frontend trước khi lên production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_PREFIX = "/api/v1"
app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(products.router, prefix=API_PREFIX)
app.include_router(cart.router, prefix=API_PREFIX)
app.include_router(orders.router, prefix=API_PREFIX)
app.include_router(reviews.router, prefix=API_PREFIX)
app.include_router(chat.router, prefix=API_PREFIX)
app.include_router(ai_agent.router, prefix=API_PREFIX)


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "Hello World"}


@app.get("/health")
def health() -> dict[str, str]:
    """Health check endpoint - dùng cho Docker healthcheck / load balancer."""
    return {"status": "ok", "app": settings.APP_NAME, "env": settings.APP_ENV}
