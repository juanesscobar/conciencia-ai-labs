# EXP-002A — Provider readiness probe: Crusoe Cloud · `zai-org/GLM-5.3-Flash`

**Estado:** Ejecutado (**REAL**, fuera del simulador) · **Clase:** *environment / provider readiness*
**Entorno:** estación local (Linux/WSL), cliente OpenAI-SDK · **Reloj:** 2026-10-15T01:38Z
**Repositorio de trabajo:** `exp-002` (este experimento) · **Etiqueta:** `REAL`

> **Nota de nombres:** **EXP-002A** es este probe **REAL**. `ai_factory_lab/fixtures/EXP-002.json` es
> otra cosa (fixture **SIMULATED** "ECC degradation", sin implementar). No se tocan entre sí.

## HYPOTHESIS

Un endpoint de inferencia hospedado en un proveedor GPU-cloud (Crusoe) responde de forma funcional a
una solicitud chat-completions estándar con el modelo `zai-org/GLM-5.3-Flash`, y expone de forma
observable el estado del resultado (`finish_reason`, tokens, presencia de razonamiento) — insumo para
decidir su incorporación al **harness de LLM** de la plataforma.

## ENVIRONMENT / SETUP

- Base URL: `https://api.inference.crusoecloud.com/v1` (contrato compatible con OpenAI).
- Modelo declarado: `zai-org/GLM-5.3-Flash`. `timeout=45 s`, `max_retries=0`, `temperature=0.2`, `max_tokens=1024`.
- `extra_body.chat_template_kwargs.reasoning_effort = "low"`.
- Credencial: `CRUSOE_API_KEY` por variable de entorno (su valor **no** se registra en ningún artefacto).
- Prompt (1 turno): *"What does GPU utilization measure? Answer in one sentence."*

## EVIDENCE

- `evidence/EXP-002A/result.json` — reporte crudo **persistido** de la corrida exitosa.
- `evidence/EXP-002A/probe.py` — script del probe (sanitizado; la key se lee de env).
- `evidence/EXP-002A/README.md` — índice de la evidencia.

## RESULTADOS OBSERVADOS (3 corridas)

Se ejecutó el mismo probe tres veces. Los tres desenlaces se documentan; **sólo la corrida exitosa
dejó artefacto persistido** (el script sobreescribe `result.json` en cada corrida, y aborta en error).

| # | Resultado observado | `finish_reason` | Evidencia |
| --- | --- | --- | --- |
| 1 | **Respuesta sin contenido visible** — `content` vacío; el script lo clasifica `incomplete` | — | Observado por el operador (JSON sobreescrito por la corrida 3) |
| 2 | **HTTP 503 `capacity_unavailable`** — el proveedor rechaza por capacidad | — | Observado por el operador (error; sin artefacto) |
| 3 | **Inferencia exitosa** — `stop`, 2.071 s, 51 tokens, sin `reasoning_content` | `stop` | **Persistida**: `evidence/EXP-002A/result.json` |

### Detalle de la corrida con evidencia persistida (corrida 3)

| Métrica | Valor |
| --- | --- |
| `status` | **success** |
| `finish_reason` | stop |
| latencia (wall-clock cliente) | 2.071 s |
| tokens prompt / completion / total | 23 / 28 / 51 |
| modelo ecoado por la API | `zai-org/GLM-5.3-Flash` |
| `reasoning_content` presente | **false** |

## INTERPRETATION

- El provider es **alcanzable** y compatible con el SDK OpenAI; el round-trip exitoso es **rápido** (~2 s).
- **No es 100 % confiable en una sola pasada:** en 3 intentos hubo 1 respuesta vacía y 1 **HTTP 503
  `capacity_unavailable`**. La indisponibilidad por capacidad es un comportamiento esperado de un
  proveedor GPU-cloud y es material para *resiliencia* (retry/backoff, fallback) — **fuera del alcance
  de EXP-002A** (ver *Coordinación*).
- `reasoning_effort="low"` fue **aceptado sin error** pero **no** se observó `reasoning_content`:
  o el modelo no expone el canal de razonamiento por esta API, o el parámetro fue **ignorado**.

## WHAT THIS PROVES / DOES NOT PROVE

- **Prueba:** conectividad, contrato de respuesta (shape OpenAI), campos de telemetría básicos
  (`finish_reason`, uso de tokens, latencia) y que el proveedor puede devolver **503 por capacidad**.
- **No prueba:** calidad del modelo, disponibilidad sostenida (SLA), rate limits, precios, ni el
  comportamiento del canal de razonamiento. No involucra GPU propia ni infraestructura de la VM.

## LIMITATIONS

- n=3; **una sola** corrida con evidencia persistida. Sin reintentos (deliberado en EXP-002A).
- El desenlace 503 y el vacío se conservan como **observaciones del operador**, no como artefactos.
- Prompt trivial; no evalúa utilidad para tareas reales del producto. No se midió costo.

## COORDINACIÓN (EXP-002B)

EXP-002A queda como **evidencia inmutable**. La resiliencia del proveedor (503/`capacity_unavailable`,
retry, observabilidad, métricas) es el foco de **EXP-002B** y **no** se aborda aquí.

## NEXT STEPS (candidato a *harness*)

1. Matriz prompt × `reasoning_effort ∈ {low, high}` para resolver el canal de razonamiento.
2. N=30 con concurrencia acotada para tasa de éxito y latencia p50/p95.
3. Si se adopta: registrar `crusoe` como provider en el *llm_harness* de la plataforma y una entrada
   de modelo `crusoe/zai-org/GLM-5.3-Flash` con su `provider_readiness`.
