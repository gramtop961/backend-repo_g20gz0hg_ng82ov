import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from pydantic import BaseModel, Field
from bson import ObjectId

app = FastAPI(title="Navkar Jewellery API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- Models ----------
class ProductIn(BaseModel):
    title: str = Field(...)
    description: Optional[str] = Field(None)
    price: float = Field(..., ge=0)
    category: str = Field(...)
    image: Optional[str] = None
    in_stock: bool = True

class ProductOut(ProductIn):
    id: str

# ---------- Utils ----------
def serialize_product(doc) -> ProductOut:
    return ProductOut(
        id=str(doc.get("_id")),
        title=doc.get("title", ""),
        description=doc.get("description"),
        price=float(doc.get("price", 0)),
        category=doc.get("category", ""),
        image=doc.get("image"),
        in_stock=bool(doc.get("in_stock", True)),
    )

# ---------- Routes ----------
@app.get("/")
def read_root():
    return {"brand": "Navkar Jewellery", "message": "Backend running"}

@app.get("/api/hello")
def hello():
    return {"message": "Hello from Navkar Jewellery backend!"}

@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        from database import db
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except ImportError:
        response["database"] = "❌ Database module not found"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"
    return response

# Products API
@app.get("/api/products", response_model=List[ProductOut])
def list_products(category: Optional[str] = None, q: Optional[str] = None, limit: int = 24):
    from database import db
    if db is None:
        return []
    filt = {}
    if category:
        filt["category"] = category
    if q:
        filt["$or"] = [
            {"title": {"$regex": q, "$options": "i"}},
            {"description": {"$regex": q, "$options": "i"}},
        ]
    cursor = db["product"].find(filt).limit(limit)
    return [serialize_product(doc) for doc in cursor]

@app.get("/api/products/{product_id}", response_model=ProductOut)
def get_product(product_id: str):
    from database import db
    if db is None:
        raise HTTPException(status_code=404, detail="Not found")
    try:
        oid = ObjectId(product_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid id")
    doc = db["product"].find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    return serialize_product(doc)

@app.get("/api/categories", response_model=List[str])
def list_categories():
    from database import db
    if db is None:
        return []
    categories = db["product"].distinct("category")
    return sorted([c for c in categories if c])

# ---------- Startup seed ----------
@app.on_event("startup")
def seed_products_if_empty():
    try:
        from database import db
        if db is None:
            return
        if db["product"].count_documents({}) == 0:
            sample_products = [
                {
                    "title": "Classic Diamond Ring",
                    "description": "Elegant 18K gold ring with a brilliant-cut diamond.",
                    "price": 499.0,
                    "category": "Rings",
                    "image": "https://images.unsplash.com/photo-1520962918287-7448c2878f65?q=80&w=1200&auto=format&fit=crop",
                    "in_stock": True,
                },
                {
                    "title": "Pearl Necklace",
                    "description": "Timeless freshwater pearl necklace for every occasion.",
                    "price": 259.0,
                    "category": "Necklaces",
                    "image": "https://images.unsplash.com/photo-1603575449299-b47a3aab52e1?q=80&w=1200&auto=format&fit=crop",
                    "in_stock": True,
                },
                {
                    "title": "Gold Hoop Earrings",
                    "description": "Minimal 22K gold hoops for daily wear.",
                    "price": 149.0,
                    "category": "Earrings",
                    "image": "https://images.unsplash.com/photo-1609250291996-fdebe6020a0b?q=80&w=1200&auto=format&fit=crop",
                    "in_stock": True,
                },
                {
                    "title": "Men's Platinum Band",
                    "description": "Comfort-fit platinum band with smooth finish.",
                    "price": 799.0,
                    "category": "Bands",
                    "image": "https://images.unsplash.com/photo-1617032884947-c6023a4e7bb9?q=80&w=1200&auto=format&fit=crop",
                    "in_stock": True,
                },
                {
                    "title": "Emerald Pendant",
                    "description": "Vibrant emerald pendant set in 18K gold.",
                    "price": 349.0,
                    "category": "Pendants",
                    "image": "https://images.unsplash.com/photo-1612177348773-2f0df2a4e93c?q=80&w=1200&auto=format&fit=crop",
                    "in_stock": True,
                },
            ]
            db["product"].insert_many(sample_products)
    except Exception:
        # Ignore startup errors to not crash server
        pass


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
