# Conventional transport

## How to Run

```bash
docker run -d \
  --name innopolis_db \
  -e POSTGRES_DB=innopolis_transit \
  -e POSTGRES_PASSWORD=postgres \
  -p 5432:5432 \
  postgres:16

pip install -r requirements.txt

uvicorn main:app --reload --host 0.0.0.0 --port 8000
```
