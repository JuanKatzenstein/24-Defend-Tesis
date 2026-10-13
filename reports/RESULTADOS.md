# Resultados — Detector de phishing en URLs/dominios

Resumen de la evaluación. Dos escenarios: (1) corpus sintético regional como
caso de estudio y (2) **datos reales** (OpenPhish + Tranco) como resultado principal.

## Fuentes de datos

| Clase | Fuente | N |
|-------|--------|---|
| Phishing | OpenPhish community feed (`openphish.com/feed.txt`) | 300 |
| Legítimas | Tranco top-list (`tranco-list.eu`) | 2000 |
| (regional) | `corpus_sintetico.csv` + hard negatives curados | 20 / 91 |

## Resultado principal (datos reales, evaluación a nivel dominio)

Para evitar un artefacto de formato (Tranco entrega dominios pelados, sin path),
se evalúa a **nivel dominio**: ambas clases se reducen a `scheme://host`
(`build_dataset.py --host-only`). Así ninguna feature de largo/slash separa por
formato en vez de por phishing.

Validación cruzada 5-fold + hold-out 30% (seed 42), 2285 dominios únicos:

| Modelo | CV-F1 | Test F1 | ROC-AUC |
|--------|------:|--------:|--------:|
| Regresión Logística | 0.88 | 0.91 | 0.969 |
| Random Forest | 0.89 | 0.90 | 0.976 |

**Robustez (ablación de features):** el rendimiento se mantiene al quitar el TLD
one-hot y los largos, e incluso usando *solo* features de mecanismo (TLD
sospechoso, hosting gratuito, marca suplantada, entropía, typosquat): RF AUC 0.982.
Es decir, la señal es real, no un atajo del armado del dataset.
Detalle en `ablacion_real_host.md`.

**Features más informativas (host-level):** largo del host, cantidad de puntos /
subdominios, entropía del dominio, ausencia de `https`, guiones. Coinciden con el
mecanismo conocido del phishing (hosts largos, muy anidados, aleatorios).

**Umbral:** F1-óptimo ≈ 0.4 (ver `real/umbral.md`); subir/bajar según costo FP/FN.

## Lección metodológica (clave para la defensa)

En **ambos** escenarios aparecieron fugas por el armado del dataset, y en ambos se
detectaron y corrigieron:

1. **Sintético:** la clase negativa "fácil" (solo dominios `.uy` oficiales) daba
   AUC 1.000 por el TLD → se agregaron *hard negatives* (logins legítimos, hosting
   de plataforma, TLDs `.xyz/.io`). AUC bajó a ~0.96–0.99.
2. **Real:** Tranco sin paths daba AUC 1.000 porque `path_len`/`n_slash` separaban
   por formato → evaluación a nivel dominio. AUC realista ~0.97.

La herramienta que expuso ambas fue `ablation.py`: **si el rendimiento no cae al
quitar features sospechosas de fuga, la señal es genuina; si se desploma, era un
atajo.** Ese es el control de calidad central del trabajo.

## Limitaciones y trabajo futuro

- **Nivel dominio** ignora la señal del path (`/login.php`, `/wp-includes/...`),
  que es real en phishing. Para aprovecharla haría falta una clase legítima con
  URLs completas (no solo dominios), p. ej. logs de navegación o Common Crawl.
- **Piso del detector solo-URL:** casos apex minimalistas sin señuelos léxicos
  (`ocazrv.xyz`) necesitan señales externas (edad del dominio, certificado,
  reputación DNS).
- **Feeds dinámicos:** OpenPhish rota; conviene fijar un snapshot y, para números
  finales, un split temporal (entrenar con phishing viejo, testear con nuevo).
