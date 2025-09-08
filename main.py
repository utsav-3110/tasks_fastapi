from contextlib import asynccontextmanager

from fastapi import FastAPI
from starlette.requests import Request
import httpx
from database import  engine , Base
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter
import redis.asyncio as redis



from  routes import main




Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    r = redis.from_url("redis://localhost", encoding="utf-8", decode_responses=True)
    await FastAPILimiter.init(r)
    yield
    await r.close()

app = FastAPI(lifespan=lifespan)

@app.middleware("http")
async def ip_logger(request: Request, call_next):
    ip =  request.client.host



    if ip == "127.0.0.1":
        geo_info = {"message": "Localhost IP - no geolocation lookup performed"}
    else:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"http://ip-api.com/json/{ip}")
                geo_info = response.json()

                with open('log.txt', 'a') as f:
                    f.write('-' * 150 + '\n')
                    f.write('IP: ' + ip + '\n')
                    f.write(
                        'Country: ' + geo_info["country"] +
                        ', Region: ' + geo_info['regionName'] +
                        ', City: ' + geo_info['city'] + '\n'
                    )
                    f.write('Latitude: ' + str(geo_info['lat']) + ', Longitude: ' + str(geo_info['lon']) + '\n')

                    f.write('-' * 150 + '\n')  # Separator line

        except Exception as e:
            geo_info = {"error": str(e)}

    response = await call_next(request)
    return response

app.include_router(main.router)
