# Conciencia AI Labs

Conciencia AI Labs is a practical research and engineering lab for experiments in AI systems,
infrastructure, reliability and agent operations. Experiments are documented with their evidence,
limitations and reproducibility status.

## Estado de los experimentos

> **Etiquetas:** `REAL` = ejecutado sobre infraestructura/proveedor real · `SIMULATED` = modelo en memoria,
> sin hardware/APIs pagas. Cada experimento declara la suya.

- **Ejecutado (real):** **EXP-003 — NVIDIA H200 GPU Inference on Nebius AI Cloud** (`REAL`):
  1× H200, CUDA 13.0, PyTorch 2.13.0+cu130, DCGM 4.7.0, Docker, vLLM 0.32.0 y
  `Qwen/Qwen3-0.6B`. Benchmark secuencial de 10 solicitudes: 1.163 tokens de salida,
  latencia media **0,20773 s** y **559,86 tokens/s** agregados. VM detenida al cierre.
  → [`exp-003/README.md`](exp-003/README.md) · [`exp-003/reports/EXP-003-H200-INFERENCE.md`](exp-003/reports/EXP-003-H200-INFERENCE.md) · [`exp-003/evidence/public/`](exp-003/evidence/public/).
- **Ejecutado (real):** **EXP-001 v0.2 — Controlled Cloud Reliability Loop** sobre una **Linux Cloud VM**
  real (workload FastAPI aislado, fallo de servicio controlado y autorizado).
  → [`docs/EXP-001-CLOUDOPS-REPORT.md`](docs/EXP-001-CLOUDOPS-REPORT.md) · [`evidence/EXP-001/`](evidence/EXP-001/).
- **Ejecutado (real):** **EXP-002A — Provider readiness probe** (`REAL`) sobre un proveedor GPU-cloud
  (Crusoe Cloud · `zai-org/GLM-5.3-Flash`): probe de conectividad/contrato de respuesta. 3 corridas:
  1 respuesta vacía, 1 **HTTP 503 `capacity_unavailable`**, 1 éxito (2.071 s, 51 tokens).
  → [`docs/EXP-002A-REPORT.md`](docs/EXP-002A-REPORT.md) · [`evidence/EXP-002A/`](evidence/EXP-002A/).
  (La resiliencia del proveedor es el foco de EXP-002B.)
- **Simulado:** EXP-001 v0.1 (simulador local, `SIMULATED`) y la validación del core en proceso.
- **Planeado:** EXP-002B…005 (fixtures de diseño; no implementados. EXP-002 es el fixture SIMULATED
  "ECC degradation"; EXP-002A es el probe REAL, distinto). EXP-003 Session 002 (8B/14B, concurrencia)
  queda como siguiente paso del experimento GPU.

EXP-001 v0.2 **no** es infraestructura GPU ni una AI Factory en producción. Ver *What this does not prove*
en su reporte. El resto de este repositorio corresponde a la parte **SIMULATED** (sin GPU real, DCGM,
APIs pagas ni infraestructura real), pensada para estudio local reproducible.

## EXP-001 — CloudOps real (v0.2)

Además del experimento SIMULATED de arriba, EXP-001 se ejecutó como **CloudOps real** sobre una VM Linux (Hetzner) con un workload FastAPI aislado (systemd, solo loopback) y un fallo de servicio **controlado y autorizado** por un humano. Resultado: **PASS** (con un gate secundario **PARTIAL**).

Circuito validado: detección → evidencia → diagnóstico → aprobación humana → remediación → verificación.

- Reporte: [`docs/EXP-001-CLOUDOPS-REPORT.md`](docs/EXP-001-CLOUDOPS-REPORT.md)
- Evidencia sanitizada: [`evidence/EXP-001/`](evidence/EXP-001/)

> No es infraestructura GPU ni una AI Factory en producción. El incidente fue intencional; ver *What this does not prove* en el reporte.

## Demo local reproducible (Python 3.11+)

Desde el checkout `ai-factory-lab`, sin instalación ni servicios:

```powershell
py -3.12 -m unittest discover -s tests -v
py -3.12 -m ai_factory_lab --fixture-decision approved --out artifacts/local-demo
```

Resultado esperado: `environment=SIMULATED`, `integration_mode=FIXTURE_ONLY`, `result=PASS`.
La decisión es **una fixture de prueba**, no aprobación humana ni integración con Conciencia.
Por defecto no hay aprobación y no se ejecuta la acción:

```powershell
py -3.12 -m ai_factory_lab
py -3.12 -m ai_factory_lab --fixture-decision rejected
py -3.12 -m ai_factory_lab --fixture-decision approved --missing-telemetry
```

Estos tres comandos terminan con exit 2, `BLOCKED` o `BLOCKED_INSUFFICIENT_EVIDENCE`. La fixture aprobada está
ligada al plan de seed 7 y reloj inicial documentado. Cambiar seed/reloj/evidencia requiere otra fixture
explícita; no se genera una aprobación automática durante la ejecución. Exit 0 solo si verificación PASS.

`result.json` y `manifest.json` identifican entorno, escenario/versiones, seed, timestamps virtuales,
procedencia, acción/objetivo/parámetros, hashes, Git y fuentes. Un repo nuevo puede no tener commit:
`git_commit=null` es deliberado, acompañado de hashes del árbol. Los hashes no autentican al aprobador.

## Exportación y captura preparada

Para entregar a la landing una comparación reproducible de las decisiones fixture (sin ejecutar controles
interactivos), generar el paquete SIMULATED:

```powershell
py -3.12 -m ai_factory_lab --export-comparison artifacts/landing-exp001
```

El handoff visual está en `docs/LANDING-PACKAGE.md`. La preparación para una captura NVIDIA/Nebius de
solo lectura, separada del análisis local y sin recursos cloud, está en `docs/NEBIUS-NVIDIA-RUNBOOK.md`.

## Contrato real del core, sin servidor

El script opt-in ejecuta **el router Signals, servicio de persistencia y gate reales** del checkout core
registrado. Sustituye únicamente la dependencia de base por SQLite en memoria y la identidad por una
fixture. No carga `app.main`, `.env`, schedulers ni endpoints remotos. No modifica el core.

```powershell
py -3.12 scripts/verify_core.py --core ../mission-control --out artifacts/local-core.json
```

Requiere FastAPI, SQLAlchemy, Pydantic y httpx disponibles en el intérprete; no son dependencias del simulador.
Se valida ausencia/rechazo/aprobación con `execute_workflow` y `approve_step`, payload HTTP real, rechazo de
Mission desconocida, acción simulada y Signal de verificación. El driver de test aprueba: **no es prueba de
autenticación, aprobación humana, roles, despliegue, PostgreSQL ni controles de presupuesto**.
Los IDs y timestamps del core varían; la reproducibilidad del modelo se verifica por separado.

## Qué demuestra y qué no

Temperatura sintética >85 °C durante tres muestras de 10 s produce diagnóstico determinista. La acción
pausa admisión en un nodo simulado. El modelo presupone fin del job y enfriamiento; cinco muestras <75 °C,
admisión detenida y cero asignaciones prueban recuperación **del modelo**. Pausar admisión no enfría por sí
solo hardware con jobs activos. El verificador también puede fallar aunque el ejecutor reporte éxito.

El core actual aprueba por step, sin vincular hash/target/identidad/expiración. El Lab conserva el plan
inmutable y revalida evidencia/revisión/target antes de mutar su estado en memoria. Esto es un invariante
del simulador, no una solución al gap de seguridad del core. Datos manipulados localmente por el operador
no constituyen una frontera de seguridad. Ver [contratos y gaps](docs/CONTRACTS.md).

## Cuatro pilares

- Portfolio: esta demo y sus artefactos se pueden reproducir sin hardware; vídeo futuro de 90 s: entorno,
  trigger, propuesta, fixture/gate, estado observado y límites. No se publicó ni desplegó.
- Educación: se practican puertos Python, reloj/seed, unidades, pruebas negativas, adaptación HTTP,
  idempotencia y observación independiente. Linux/redes/CUDA/Kubernetes/DCGM quedan como aprendizaje futuro;
  ejecutar tests no certifica aprendizaje del operador.
- Investigación: hipótesis: gates e invariantes reducen ejecuciones no autorizadas en este modelo.
  Método: misma entrada, tres decisiones; control con evidencia incompleta y recuperación fallida.
  Resultados concretos en `artifacts/` y reporte; no se comparó un agente LLM ni hardware físico.
- Negocio: hipótesis de valor en integración y trazabilidad de operaciones. Faltan entrevistas autorizadas,
  comparación con runbooks/nativas NVIDIA, medición de tiempo humano y disposición a pagar. No hay ahorro
  económico medido ni presupuesto aplicado.

## Próxima etapa

Ampliar adversariales y controlar el binding de aprobación en el core mediante una fase separada autorizada.
Después implementar EXP-002B..005 y observabilidad. Para EXP-003, ejecutar Session 002 con modelos 8B/14B,
concurrencia, TTFT y conciliación de costos. No hay procesos persistentes necesarios en v0.1.
Si se requiere un core persistente, usar su runbook en otra sesión autorizada, nunca apuntar esta demo a producción.
