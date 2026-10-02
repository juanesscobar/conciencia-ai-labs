# Contratos — SIMULATED

`InventoryTelemetry`: capabilities, snapshot, query_metrics, list_jobs.
`ActionExecutor`: plan_action, execute, get_operation.
`OutcomeVerifier`: verify. Son Protocols internos del Lab, no APIs NVIDIA.

`SimulatedGPUProvider` solo admite `pause_admission`; otras acciones son unsupported.
Tres muestras consecutivas, completas, del mismo target, SIMULATED y separadas por 10 s son requisito.
El executor exige observación aprobada del gate, hash del plan, evidencia vigente, revisión y target.
No hay registro/persistencia/emisión de aprobaciones dentro del Lab: `GateObservation` es un valor recibido
del adaptador o una fixture. Solo protege la transición local, no autentica su origen.

## Core inspeccionado: 383ac44, rama v2-refactor

`backend/app/routers/signals.py::SignalCreate` exige mission_id y title (1..200 caracteres); admite type,
summary, source_step, agent_id, agent_name y evidences. EvidenceIn exige content **string**; kind=data es válido.
`signal_service.create_signal` valida UUID y existencia de Mission y enum type/kind. HTTP 201 retorna id,
mission_id, type, title, status y **evidence** (singular); el request usa **evidences**. Los IDs de correlación
del Lab viajan en summary/content/source; el schema HTTP no admite workflow_run_id aunque el servicio sí.
El adaptador no inventa campos HTTP ni anuncia que fueron persistidos. Errores/timeout/acuse malformado
no producen éxito; no reintenta POST automáticamente porque el endpoint no ofrece idempotencia.

`LocalHTTPTransport` es opt-in, loopback, timeout 5 s y sin redirects. No se invoca en la demo offline.
No se guardan tokens en artefactos. Verificación con TestClient prueba HTTP in-process, no una instancia viva.

## Gate y D2

`execute_workflow` pausa ante `approval:true`. `approve_step` exige run pausado y step esperando aprobación;
marca approved/rejected y avanza a step_index+1. **El cuerpo del step aprobado se omite.** Por eso la prueba
usa un step dedicado a revisión y ejecuta la transición simulada separada tras observar el resultado.
Los servicios y modelos reales se ejecutan contra DB in-memory; la identidad es fixture.

Mission del core NO exige cliente: project_id y requester_id son opcionales; no existe campo client en
MissionCreate. El protocolo del workspace sí exige un cliente registrado para Missions de workspace.
Conciencia es la organización propietaria identificada por el prompt; se registra como cliente interno
sin inventar razón social, facturación o tenancy. Este registro no se envía como campo desconocido al core.

## Gaps que NO se cierran aquí

- Core: aprobación sin binding de plan/evidencia/target, sin identidad verificable/expiración; contrato
  propuesto: autorización referida a run, step, hash de plan/evidencia, target, revisión, actor y expiry,
  revalidada atómicamente con idempotencia y estado. Requiere cambio del core, no autorizado en esta fase.
- Policy almacenada no implica evaluación; no se acredita enforcement de rol ni límite de presupuesto.
- Falta acuse idempotente de ingesta Signals; timeout significa resultado UNKNOWN, no fracaso definitivo.
- El payload HTTP no recibe workflow_run_id; correlación en contenido no equivale a FK normalizada.
- Verificación de hardware, DCGM/NVIDIA, scheduler y energía reales no realizadas.
- El gate débil basta para demostrar el flujo SIMULATED, nunca para habilitar acciones físicas.

La integración local aislada no queda bloqueada por D2. La integración de producción y acciones reales
siguen fuera de alcance y bloqueadas por estos contratos de seguridad pendientes.
