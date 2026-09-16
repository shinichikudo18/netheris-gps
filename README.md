# Netheris GPS

Aplicación de navegación Android de Netheris, pensada para evolucionar desde un MVP móvil hacia integración con Android Auto.

## Estado

### MVP 0.1
- Kotlin
- Jetpack Compose
- MapLibre Native
- Mapa inicial centrado en Santiago de Chile
- Permisos de ubicación
- Acción **Mi ubicación**
- Acción **Casa** preparada para la siguiente fase
- Interfaz oscura inspirada en Netheris

### MVP 0.2 — siguiente objetivo
- Marcador propio de Netheris
- Guardar coordenadas de Casa localmente
- Botón Casa funcional
- Primera ruta real origen → destino
- Preparar separación entre UI, ubicación, mapa y navegación

## Arquitectura objetivo

```text
app/src/main/java/.../
├── MainActivity.kt
├── ui/
├── map/
├── location/
└── navigation/
```

## Stack
- Kotlin
- Jetpack Compose
- MapLibre Native Android
- Android Location APIs

## Roadmap
1. MVP móvil con mapa y GPS
2. Destinos guardados y ruta básica
3. Motor de navegación y pasos de ruta
4. UI Netheris completa
5. Integración Android Auto
6. Integración futura con servicios Netheris/Katherine
