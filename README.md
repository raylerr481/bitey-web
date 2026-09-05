# Bitey IA Web — General Integral AI

`bitey-web` es la plataforma general/integral de **Bitey IA**. Es la capa superior de inteligencia, memoria, planificación, evaluación, herramientas, modelos y políticas del ecosistema.

## Arquitectura de módulos

```text
                         BITEY IA WEB
                  General / Integral AI
                           │
             ┌─────────────┼─────────────┐
             │             │             │
          JobIA         Bitey SBT    futuros módulos
       empleo IA       trading IA
             │
             ▼
       JobIA Backend
             │
       ┌─────┴─────┐
       ▼           ▼
  JobIA-Web    JobIA-app
  web client   Android client
```

**JobIA es un módulo especializado de Bitey IA Web.** Su dominio es empleo y oportunidades profesionales. No sustituye al cerebro general de Bitey.

## Responsabilidades de Bitey IA Web

Bitey conserva la autoridad sobre:

- comprensión general de contexto e intención;
- planificación y descomposición de tareas;
- memoria y conocimiento;
- selección de herramientas;
- selección y enrutamiento de modelos;
- evaluación, contradicción y confianza;
- permisos y políticas de riesgo;
- aprendizaje y observaciones;
- workspace y capacidades generales.

Los modelos son trabajadores de inferencia reemplazables. Bitey no depende de un único modelo.

## JobIA como módulo

JobIA implementa la capacidad especializada de empleo mediante un backend propio y un contrato versionado `jobia-v1`.

```text
Bitey IA Web
     │
     │ módulo / capacidad
     ▼
   JobIA Backend
     │
     ├── oportunidades
     ├── matching / ranking
     ├── perfiles
     ├── aplicaciones
     └── alertas
     │
     ├───────────────┐
     ▼               ▼
 JobIA-Web       JobIA-app
```

El backend de JobIA puede solicitar capacidades cognitivas de Bitey cuando una tarea lo requiera, pero los clientes nunca deben depender de detalles internos del cerebro.

## Bitey Trainer

`bitey-trainer` es el motor interno de entrenamiento y validación de las capacidades especializadas de JobIA. No es un cliente ni un segundo cerebro.

```text
Bitey Trainer → valida capacidades → JobIA → clientes
```

## Clientes JobIA

- **JobIA-Web:** frontend web oficial.
- **JobIA-app:** aplicación Android oficial.

Ambos consumen el mismo backend JobIA. Ninguno contiene credenciales privadas ni implementa un backend paralelo.

## Datos y memoria

Supabase/Postgres es la capa persistente canónica de Bitey IA Web cuando se requiere persistencia. Los módulos deben acceder a datos mediante contratos y aislamiento adecuados.

No se introduce Neo4j ni MongoDB como dependencia arquitectónica.

## Política de coste

El diseño es free-first:

- sin fallback silencioso a pago;
- modelos locales/open-weight cuando estén disponibles;
- proveedores gratuitos verificados cuando corresponda;
- herramientas deterministas para tareas que no necesitan LLM;
- degradación controlada cuando un proveedor no esté disponible.

No se requiere Gemini API.

## Seguridad

- Secretos exclusivamente del lado servidor.
- Modelos externos tratados como entradas no confiables hasta evaluación.
- Herramientas con permisos explícitos.
- Contexto privado aislado por usuario/tenant.
- Acciones de impacto requieren autorización.
- Los módulos se comunican mediante contratos versionados.

## Principio

> **Bitey IA Web es el sistema general. JobIA es un módulo de empleo. JobIA es su backend especializado. JobIA-Web y JobIA-app son clientes del mismo backend. Bitey Trainer entrena y valida las capacidades de JobIA.**
