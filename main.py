import io
import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from PIL import Image
import imagehash

app = FastAPI(title="pHash Microservice")

class HashRequest(BaseModel):
    image_url: str

@app.post("/phash")
def get_phash(data: HashRequest):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        }
        response = requests.get(data.image_url, headers=headers, timeout=10)
        response.raise_for_status()

        image = Image.open(io.BytesIO(response.content))
        calculated_hash = str(imagehash.phash(image))

        return {"phash": calculated_hash}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Blad przetwarzania: {str(e)}")

@app.get("/health")
def health():
    return {"status": "ok"}
