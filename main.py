import io
import requests
import imagehash
from PIL import Image
from fastapi import FastAPI, HTTPException, Request

app = FastAPI(title="Empco pHash API")

BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "image/jpeg,image/png,image/webp,*/*;q=0.8",
    "Referer": "https://www.sklepbaterie.pl/"
}


def compute_phash_from_bytes(image_bytes: bytes) -> str:
    try:
        with Image.open(io.BytesIO(image_bytes)) as img:
            # Natychmiastowe zmniejszenie dużych grafik przed alokacją tła w RAM
            img.thumbnail((256, 256))

            # Konwersja palet kolorów i kanału alfa (PNG/WebP) do standardowego RGB
            if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
                background = Image.new("RGB", img.size, (255, 255, 255))
                alpha_img = img.convert("RGBA")
                background.paste(alpha_img, mask=alpha_img.split()[3])
                img = background
            elif img.mode != "RGB":
                img = img.convert("RGB")

            return str(imagehash.phash(img))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Błąd przetwarzania obrazu: {str(exc)}")

@app.get("/")
def health_check():
    return {"status": "ok"}


@app.post("/phash")
async def get_phash(request: Request):
    content_type = request.headers.get("content-type", "").lower()

    # SCENARIUSZ A: Plik binarny przesłany z n8n jako Form-Data (pole 'image' lub 'file')
    if "multipart/form-data" in content_type:
        form = await request.form()
        upload = (
            form.get("image")
            or form.get("file")
            or next((val for val in form.values() if hasattr(val, "read")), None)
        )

        if not upload or not hasattr(upload, "read"):
            raise HTTPException(
                status_code=400,
                detail="Nie znaleziono pliku binarnego w polu 'image' ani 'file'."
            )

        image_bytes = await upload.read()
        if not image_bytes:
            raise HTTPException(status_code=400, detail="Przesłany plik jest pusty.")

        phash_value = compute_phash_from_bytes(image_bytes)
        return {"phash": phash_value, "filename": getattr(upload, "filename", "uploaded_image")}

    # SCENARIUSZ B: Kompatybilność wsteczna dla zapytań JSON {"image_url": "..."}
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Nieprawidłowy format żądania (oczekiwano Form-Data lub JSON).")

    image_url = payload.get("image_url") if isinstance(payload, dict) else None
    if not image_url:
        raise HTTPException(status_code=400, detail="Brak pola 'image_url' w treści JSON.")

    try:
        resp = requests.get(image_url, headers=BROWSER_HEADERS, timeout=15)
        resp.raise_for_status()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Nie udało się pobrać obrazu z URL: {str(exc)}")

    phash_value = compute_phash_from_bytes(resp.content)
    return {"phash": phash_value, "image_url": image_url}
