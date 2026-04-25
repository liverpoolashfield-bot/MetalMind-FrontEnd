import os
import stripe
from fastapi import FastAPI, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from dotenv import load_dotenv
from typing import Optional

load_dotenv()

# Stripe configuration
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
PRICE_IDS = {
    "basic": os.getenv("STRIPE_PRICE_BASIC"),
    "professional": os.getenv("STRIPE_PRICE_PRO"),
    "enterprise": os.getenv("STRIPE_PRICE_ENT"),
}

# Simple in‑memory user store (could be persisted later)
# In a real app this would be ArangoDB – here we keep a dict keyed by username.
users_db = {}

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

# JWT settings
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change_me")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 30  # 30 days

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")

class Token(BaseModel):
    access_token: str
    token_type: str

class User(BaseModel):
    username: str
    tier: str = "free"

def create_access_token(data: dict):
    to_encode = data.copy()
    # Normally add expiration, omitted for simplicity
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_user(username: str) -> Optional[dict]:
    return users_db.get(username)

def authenticate_user(username: str, password: str):
    user = get_user(username)
    if not user:
        return False
    if not verify_password(password, user["hashed_password"]):
        return False
    return user

async def get_current_user(token: str = Depends(auth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = get_user(username)
    if user is None:
        raise credentials_exception
    return User(username=username, tier=user.get("tier", "free"))

app = FastAPI()

# ---- Auth Endpoints ----
@app.post("/register", response_model=Token)
async def register(form: OAuth2PasswordRequestForm = Depends()):
    if form.username in users_db:
        raise HTTPException(status_code=400, detail="Username already exists")
    hashed = get_password_hash(form.password)
    users_db[form.username] = {"username": form.username, "hashed_password": hashed, "tier": "free"}
    access_token = create_access_token(data={"sub": form.username})
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/token", response_model=Token)
async def login(form: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form.username, form.password)
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    access_token = create_access_token(data={"sub": form.username})
    return {"access_token": access_token, "token_type": "bearer"}

# ---- User Tier ----
@app.get("/user/tier")
async def read_tier(current: User = Depends(get_current_user)):
    return {"tier": current.tier}

# ---- Stripe Checkout ----
@app.post("/payment/create-session")
async def create_checkout_session(tier: str, current: User = Depends(get_current_user)):
    if tier not in PRICE_IDS:
        raise HTTPException(status_code=400, detail="Invalid tier")
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="subscription",
            line_items=[{
                "price": PRICE_IDS[tier],
                "quantity": 1,
            }],
            success_url="http://localhost:8080/?session_id={CHECKOUT_SESSION_ID}",
            cancel_url="http://localhost:8080/",
            client_reference_id=current.username,
        )
        return {"sessionId": session.id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ---- Stripe Webhook ----
@app.post("/payment/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except Exception as e:
        raise HTTPException(status_code=400, detail="Webhook signature verification failed")
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        username = session.get("client_reference_id")
        price_id = session["subscription"]  # we will fetch subscription to get price
        # Retrieve subscription to get price_id
        sub = stripe.Subscription.retrieve(session["subscription"])
        price = sub["items"]["data"][0]["price"]["id"]
        tier = None
        for k, v in PRICE_IDS.items():
            if v == price:
                tier = k
                break
        if username and tier:
            user = users_db.get(username)
            if user:
                user["tier"] = tier
    return {"status": "success"}

# ---- Downgrade / Cancel (Customer Portal) ----
@app.post("/payment/portal")
async def create_portal_session(current: User = Depends(get_current_user)):
    # For demo: return a message since we don't have Stripe customer ID mapping
    # In production, store stripe_customer_id when user first subscribes
    raise HTTPException(status_code=400, detail="Portal not available in demo mode")
