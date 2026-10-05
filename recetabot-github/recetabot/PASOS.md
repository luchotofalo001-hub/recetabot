# Desde cero

Las recetas no van en tu computadora ni en GitHub. Se cargan una vez en Supabase y el archivo local se borra.

## 1. Telegram

1. En Telegram, abrí @BotFather.
2. `/newbot`. Poné nombre y usuario. Copiá el token.
3. Escribile `/start` a tu bot.
4. En el navegador abrí `https://api.telegram.org/botTU_TOKEN/getUpdates`.
5. Copiá el número de `chat.id`.

## 2. Gemini

1. Entrá a https://aistudio.google.com/apikey.
2. Create API key y copiala.

## 3. Supabase

1. Entrá a https://supabase.com/dashboard y creá un proyecto.
2. Settings → API. Copiá Project URL y la clave `service_role`. No uses la anon.
3. SQL Editor → New query. Pegá todo el archivo `supabase/schema.sql` y apretá Run.

## 4. Cargar las recetas una sola vez

En una carpeta temporal, con el archivo `cocineros_recetas.db` que ya tenés:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export SUPABASE_URL="https://xxxx.supabase.co"
export SUPABASE_SERVICE_ROLE_KEY="eyJ..."
PYTHONPATH=. python scripts/seed_supabase.py /ruta/cocineros_recetas.db
```

En Windows el activate es `.venv\Scripts\activate`.

Cuando termine, en Supabase → Table Editor → `recipes` tienen que verse miles de filas. Ahí borralo de la computadora:

```bash
rm /ruta/cocineros_recetas.db
```

Render no usa ese archivo. Lee Supabase.

## 5. GitHub

1. https://github.com/new → repo `recetabot`, privado, sin README.
2. Dentro de la carpeta del bot, sin el `.db` y sin `.env`:

```bash
git init
git add .
git commit -m "bot de recetas"
git branch -M main
git remote add origin https://github.com/TU_USUARIO/recetabot.git
git push -u origin main
```

## 6. Render

1. https://render.com → New → Web Service → el repo `recetabot`.
2. Build: `pip install -r requirements.txt`
3. Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. Health check path: `/health`
5. Variables:

| Variable | Valor |
|---|---|
| TELEGRAM_TOKEN | token de BotFather |
| GEMINI_API_KEY | clave de AI Studio |
| GEMINI_MODEL | gemini-2.5-flash |
| SUPABASE_URL | Project URL |
| SUPABASE_SERVICE_ROLE_KEY | service_role |
| PUBLIC_URL | la URL que te da Render, sin barra final |
| WEBHOOK_SECRET | una frase larga |
| ALLOWED_CHAT_IDS | tu chat.id |

6. Deploy. Al arrancar registra el webhook. Abrí `https://TU-SERVICIO.onrender.com/health` y tiene que decir `ok`.

## 7. UptimeRobot

1. https://uptimerobot.com → Add Monitor.
2. HTTP(s), `https://TU-SERVICIO.onrender.com/health`, cada 5 minutos.
3. Evita que el plan gratis de Render se duerma.

## 8. Probar

- `tengo 4 huevos, 1 kg de papa, 1 cebolla`
- `/heladera`
- `cena rápida para 2, una vegetariana`
- `voy a hacer la 1 del primero y la 3 del segundo`
- `saca la cebolla, se pudrió`
