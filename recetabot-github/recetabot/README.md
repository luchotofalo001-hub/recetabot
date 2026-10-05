# Recetabot

Bot de Telegram. Gemini solo entiende el mensaje. Python busca recetas, estima tiempo y lleva la heladera.

## Qué carga el bot

- Recetas de Cocineros Argentinos, con cantidades tomadas de la página al pedir el detalle.
- Recetas propias con `/cargar`.
- Heladera: lo que hay en casa, con cantidad.

## Frases

- `tengo 6 huevos, 1 lechuga, 1 l de leche, 2 kg de papa`
- `/heladera`
- `saca la lechuga, se pudrió`
- `cena rápida para 2, una vegetariana` (usa la heladera sola)
- `la hice` o el botón Hice: no la repite por 2 días y descuenta cantidades.
- `/cargar` seguido de título, ingredientes con gramos y pasos.

Si Supabase ya existía:

```sql
alter table recipes add column if not exists amounts text[] default '{}';
create table if not exists pantry (
  id bigserial primary key,
  chat_id bigint not null,
  name text not null,
  qty numeric,
  unit text,
  updated_at timestamptz default now(),
  unique (chat_id, name)
);
```
