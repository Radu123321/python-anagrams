import time
import logging
import re
import html
from functools import wraps, lru_cache
from typing import Annotated, List
from datetime import datetime

from fastapi import FastAPI, Depends, HTTPException, Path, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session 
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy import func
from pydantic import BaseModel, constr

# rate limit
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

# piesele din database.py
from database import SessionLocal, Word

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler("server.log"), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Anagram Scalable API")

#  rata de limitari
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

app.add_exception_handler(
    RateLimitExceeded,
    lambda request, exc: JSONResponse(
        status_code=429,
        content={"detail": "Prea multe requesturi. Incearca mai tarziu."}
    )
)

app.add_middleware(SlowAPIMiddleware)

# Schema pentru validarea body-ului la POST/PUT
class WordSchema(BaseModel):
    word: constr(
        strip_whitespace=True,
        min_length=1,                 ##!!! fara XSS attacks
        max_length=50, 
        pattern="^[a-zA-Z]+$"  
    )

class AnagramResponse(BaseModel):
    word: str
    anagrams: List[str]
    count: int
    cached: bool

ValidWord = Annotated[str, Path(pattern="^[a-zA-Z]+$")]


#cat dureaza un api-request(asincron)
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.perf_counter()
    response = await call_next(request)
    process_time = (time.perf_counter() - start_time) * 1000
    response.headers["X-Process-Time-MS"] = f"{process_time:.4f}"
    logger.info(f"Path: {request.url.path} | Time: {process_time:.2f}ms")
    return response

#un decorator pentru perfonta, in functie de masina virtuala unde lucram
def monitor_performance(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        process_time = (end_time - start_time) * 1000
        print(f"Executie '{func.__name__}': {process_time:.4f}ms")
        return result
    return wrapper

# dependence pentru db, folosim functie generator
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# cache local(mai tarziu poate redis)
@lru_cache(maxsize=2048)
def fetch_from_db_cached(sorted_key: str):
    db = SessionLocal()
    # Cautarea in B-Tree
    results = db.query(Word.original_word).filter(Word.sorted_word == sorted_key).all()
    db.close()
    return [r[0] for r in results]

@app.get("/anagrams/{word}", response_model=AnagramResponse)
@limiter.limit("30/minute")   # rate limit
@monitor_performance
def get_anagrams(word: ValidWord, request: Request):
    clean_word = word.lower().strip()
    
    search_key = "".join(sorted(clean_word))
    
    hits_before = fetch_from_db_cached.cache_info().hits
    all_matches = fetch_from_db_cached(search_key)
    hits_after = fetch_from_db_cached.cache_info().hits
    
    anagrams = [w for w in all_matches if w != clean_word]
    
    return AnagramResponse(
        word=clean_word,
        anagrams=anagrams,
        count=len(anagrams),
        cached=(hits_after > hits_before)
    )

@app.post("/words")
@limiter.limit("10/minute")   #rata de limitare
@monitor_performance
def upsert_word(payload: WordSchema, request: Request, db: Session = Depends(get_db)):
    clean_word = payload.word.lower().strip()
    if not re.match("^[a-zA-Z]+$", clean_word):
        logger.warning(f"Suspicious input: {clean_word}")
        raise HTTPException(status_code=400, detail="Invalid characters")
    safe_word = html.escape(clean_word)

    sorted_v = "".join(sorted(clean_word))
    
    stmt = sqlite_insert(Word).values(
        original_word=safe_word,
        sorted_word=sorted_v,
        last_accessed=datetime.utcnow()
    ).on_conflict_do_update(
        index_elements=['original_word'],
        set_={'last_accessed': datetime.utcnow()}
    )
    
    try:
        db.execute(stmt)
        db.commit()
        fetch_from_db_cached.cache_clear()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Database error")
    
    return {"status": "success", "processed_word": safe_word}

@app.put("/words/{old_word}")
@limiter.limit("10/minute")   # rate limit
@monitor_performance
def update_word(old_word: ValidWord, request: Request, payload: WordSchema, db: Session = Depends(get_db)):
    db_word = db.query(Word).filter(Word.original_word == old_word.lower()).first()
    if not db_word:
        raise HTTPException(status_code=404, detail="Cuvantul original nu a fost gasit")

    new_word = payload.word.lower().strip()
    
    # Unique Constraint Error!!!
    existing = db.query(Word).filter(Word.original_word == new_word).first()
    if existing and old_word.lower() != new_word:
        raise HTTPException(status_code=400, detail="Noul cuvant exista deja in baza de date")

    db_word.original_word = html.escape(new_word)
    db_word.sorted_word = "".join(sorted(new_word))
    db_word.last_accessed = datetime.utcnow()

    try:
        db.commit()
        fetch_from_db_cached.cache_clear()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Eroare interna la salvare")
        
    return {"status": "success", "updated_to": new_word}

@app.patch("/words/{word}/touch")
@limiter.limit("20/minute")   # rata de limitare
@monitor_performance
def touch_word(word: ValidWord, request: Request, db: Session = Depends(get_db)):
    db_word = db.query(Word).filter(Word.original_word == word.lower()).first()
    if not db_word:
        raise HTTPException(status_code=404, detail="Cuvantul nu exista")
    
    db_word.last_accessed = datetime.utcnow()
    db.commit()
    return {"status": "success", "message": "Timestamp actualizat"}

@app.delete("/words/{word}")
@limiter.limit("5/minute") 
@monitor_performance
def delete_word(word: ValidWord, request: Request, db: Session = Depends(get_db)):
    db_word = db.query(Word).filter(Word.original_word == word.lower()).first()
    if not db_word:
        raise HTTPException(status_code=404, detail="Cuvantul nu exista")
    
    try:
        db.delete(db_word)
        db.commit()
        fetch_from_db_cached.cache_clear()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Database error")
    
    return {"status": "success", "message": f"Cuvantul '{word}' a fost eliminat"}