from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Optional
from sqlalchemy.orm import Session
from datetime import date, datetime

from .database import SessionLocal, init_db
from .models import Product, Sale

# Prometheus metrics
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response

app = FastAPI(title="Supermarket Sales API", version="1.0.0")

REQUEST_COUNT = Counter("http_requests_total", "Total HTTP requests", ["method", "endpoint", "http_status"]) 
SALE_COUNT = Counter("sales_total", "Total sales recorded")
REQUEST_LATENCY = Histogram("http_request_latency_seconds", "Latency of HTTP requests", ["endpoint"]) 

class ProductIn(BaseModel):
    name: str = Field(..., min_length=1)
    price: float = Field(..., gt=0)

class ProductOut(BaseModel):
    id: int
    name: str
    price: float
    class Config:
        orm_mode = True

class SaleIn(BaseModel):
    product_id: int
    quantity: int = Field(..., gt=0)

class SaleOut(BaseModel):
    id: int
    product_id: int
    quantity: int
    total: float
    created_at: datetime
    class Config:
        orm_mode = True


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.on_event("startup")
def on_startup():
    init_db()

# Middleware-like wrapper for metrics
from starlette.middleware.base import BaseHTTPMiddleware

class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        start = datetime.now()
        response = await call_next(request)
        elapsed = (datetime.now() - start).total_seconds()
        endpoint = request.url.path
        REQUEST_LATENCY.labels(endpoint=endpoint).observe(elapsed)
        REQUEST_COUNT.labels(method=request.method, endpoint=endpoint, http_status=str(response.status_code)).inc()
        return response

app.add_middleware(MetricsMiddleware)

@app.get("/healthz")
def healthz():
    return {"status": "ok"}

@app.get("/metrics")
def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.post("/products", response_model=ProductOut, status_code=201)
def create_product(payload: ProductIn, db: Session = Depends(get_db)):
    exists = db.query(Product).filter(Product.name == payload.name).first()
    if exists:
        raise HTTPException(status_code=400, detail="Product already exists")
    p = Product(name=payload.name, price=payload.price)
    db.add(p)
    db.commit()
    db.refresh(p)
    return p

@app.get("/products", response_model=List[ProductOut])
def list_products(db: Session = Depends(get_db)):
    return db.query(Product).order_by(Product.id).all()

@app.post("/sales", response_model=SaleOut, status_code=201)
def create_sale(payload: SaleIn, db: Session = Depends(get_db)):
    product = db.get(Product, payload.product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    total = product.price * payload.quantity
    s = Sale(product_id=product.id, quantity=payload.quantity, total=total)
    db.add(s)
    db.commit()
    db.refresh(s)
    SALE_COUNT.inc()
    return s

@app.get("/sales", response_model=List[SaleOut])
def list_sales(db: Session = Depends(get_db)):
    return db.query(Sale).order_by(Sale.created_at.desc()).all()

class DailyReport(BaseModel):
    date: date
    total_revenue: float
    total_items: int

@app.get("/reports/daily", response_model=DailyReport)
def daily_report(d: Optional[date] = None, db: Session = Depends(get_db)):
    if d is None:
        d = date.today()
    start_dt = datetime.combine(d, datetime.min.time())
    end_dt = datetime.combine(d, datetime.max.time())
    q = db.query(Sale).filter(Sale.created_at >= start_dt, Sale.created_at <= end_dt)
    total_revenue = sum(s.total for s in q)
    total_items = sum(s.quantity for s in q)
    return DailyReport(date=d, total_revenue=total_revenue, total_items=total_items)
