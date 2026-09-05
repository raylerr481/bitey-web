# Bitey IA Web — política de componentes propios y sin costo

## Regla arquitectónica

Bitey IA Web debe poder funcionar sin una plataforma propietaria de pago. La
capacidad central pertenece a Bitey; el software externo solo puede aportar
infraestructura reemplazable.

### Clasificación obligatoria

1. **Propio de Bitey** — cerebro cognitivo, planificación, evaluación,
   políticas, registro de herramientas, contratos de capacidades, workspace y
   ciclo de artefactos.
2. **Open source / libre** — librerías y runtimes necesarios para implementar
   esas capacidades cuando no tenga sentido reimplementarlos.
3. **Proveedor externo gratuito opcional** — solo para inferencia u otra
   capacidad sustituible, con verificación explícita de gratuidad.

Un proveedor externo nunca puede ser requisito arquitectónico.

## Prohibiciones

- No dependencia obligatoria de APIs propietarias de pago.
- No fallback silencioso hacia rutas de pago.
- No Gemini.
- No Neo4j.
- No MongoDB.
- No claves de proveedores dentro del frontend.
- No vendor lock-in en el núcleo cognitivo.

## Estrategia de inferencia

La prioridad es:

`determinista propio → modelo local/open-weight → proveedor externo gratuito verificado`

Si ninguna ruta gratuita está disponible, Bitey falla de forma explícita y
segura. No realiza cobros ni cambia de proveedor silenciosamente.

## Datos y memoria

Supabase/Postgres y pgvector permanecen como la capa persistente canónica del
ecosistema actual. La lógica cognitiva no debe quedar acoplada a un proveedor
de modelos.

## Principio de diseño

> Bitey decide qué necesita hacer antes de decidir qué herramienta o modelo
> necesita usar.

Por tanto, copiar funcionalidades de plataformas como Skywork sirve como
referencia funcional de producto, pero no convierte a Skywork ni a ninguna
otra plataforma en dependencia de Bitey.
