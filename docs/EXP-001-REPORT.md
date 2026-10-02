# EXP-001 — SIMULATED research report

Fecha: 2026-09-30. Escenario 0.1.0, generador 0.1.0, seed 7, reloj virtual
2026-09-30T00:00:00+00:00 con paso de 10 s. Infraestructura: modelo en memoria, sin GPU.

## HYPOTHESIS

Un diagnóstico determinista más observación de gate e invariantes locales impide la acción simulada
cuando falta autorización o evidencia. Una respuesta exitosa del executor no basta para probar recuperación.

## EXPERIMENT

Fixture: temperaturas base 65, 88, 89 y 90 °C, con ruido acotado y seed fija. Tres muestras >85 °C
activan recomendación de pausar admisión de sim-node-001. Se compara la misma serie con gate aprobado,
rechazado y ausente, más una serie con dato faltante. El test negativo de recuperación mantiene >85 °C
después de la acción. Baseline sano y muestras desordenadas/duplicadas se ejercitan en tests.

Las decisiones offline son fixtures explícitas. La integración en proceso usa el gate real y una decisión
del driver de test, no una persona ni un token de producción. No se prueba un agente LLM ni se replica
un motor de aprobación. El verificador observa cinco nuevas muestras y no recibe como prueba el status
del executor. La recuperación presupone fin del job y enfriamiento sintético.

## EVIDENCE

- `artifacts/exp001-approved/{result,manifest}.json`: acción y verificación.
- `artifacts/exp001-rejected/{result,manifest}.json`: rechazo sin acción.
- `artifacts/exp001-absent/{result,manifest}.json`: ausencia sin acción.
- `artifacts/exp001-missing/{result,manifest}.json`: evidencia incompleta.
- `artifacts/tests.txt`: determinismo, targets, revisión, evidencia, freshness, fallos de verificación y adaptador.
- `artifacts/core-in-process.json`: router/servicio Signals y gate reales del core; hashes y commit de origen.

## RESULT

| Condición | Resultado | Mutación simulada |
| --- | --- | --- |
| Gate fixture aprobado, plan correcto | PASS de verificación | Admisión pausada |
| Gate ausente | BLOCKED | Ninguna |
| Gate rechazado | BLOCKED | Ninguna |
| Telemetría incompleta | BLOCKED_INSUFFICIENT_EVIDENCE | Ninguna |
| Target o parámetros distintos al plan observado | Denegado en test | Ninguna |
| Recuperación térmica no ocurre | FAIL pese a executor succeeded | Admisión pausada, sin falsa recuperación |
| Timeout/error/acuse inválido de Signals | AdapterError; delivery no confirmado | Sin reintento automático |

Tests reproducen mismo payload canónico con seed/reloj iguales; otro seed cambia telemetría.
Son pruebas funcionales pequeñas, no estimaciones estadísticas de confiabilidad de agentes ni de MTTR.
El resultado del gate real en memoria se identifica CORE_IN_PROCESS; el modelo físico sigue SIMULATED.

## CONCLUSION

La sección vertical funciona para el modelo definido y muestra denegación y verificación independiente.
La aprobación del core sigue sin ligarse a target/hash/identidad/expiración. El invariante local de un
proceso controlado no sustituye esa garantía. No se demostraron ahorro, reducción de incidentes reales,
seguridad multiusuario, roles, policy, budget enforcement ni compatibilidad NVIDIA/DCGM.

Aprendizaje practicado por la implementación: puertos, modelos reproducibles, contratos HTTP, idempotencia,
pruebas adversariales y límites de evidencia. Aprendizaje humano: pendiente de ejecutar/explicar la demo.
Hipótesis de negocio: valor en integrar trazabilidad y revisión; faltan usuarios, baseline de tiempo y
validación de disposición a pagar. Siguiente investigación: fallo de ingesta tras escritura y reintentos,
evidencia conflictiva, workloads que no terminan, y comparación con runbooks sobre más seeds.
