# Resultados — Detector de phishing en URLs/dominios

Resumen de la evaluación. Dos escenarios: (1) corpus sintético regional como
caso de estudio y (2) **datos reales** (OpenPhish + Tranco) como resultado principal.

## Fuentes de datos

| Clase | Fuente | N |
|-------|--------|---|
| Phishing | OpenPhish community feed (`openphish.com/feed.txt`) | 300 |
| Legítimas | Tranco top-list (`tranco-list.eu`) | 2000 |
| Phishing + legítimas | **Corpus curado `Corpus_VF`** (dominios etiquetados a mano) | 1160 / 1279 |
| (regional) | `corpus_sintetico.csv` + hard negatives curados | 20 / 91 |

### Dataset combinado (corpus curado + feeds reales)

Uniendo el corpus curado con los feeds reales, deduplicando por host, el dataset
a nivel dominio queda en **4.633 dominios únicos (1.440 phishing / 3.193 legítimos)**.
Se etiqueta la región de cada host (`src/ingest_corpus.py` → `corpus_regiones.csv`):
**42 phishing UY** (BROU, SUCIVE, Antel, Prex, OCA, Redpago) + 144 legítimos `.uy`,
398 phishing BR y el resto LATAM/global. Reproducir con:

```bash
cd src
python3 ingest_corpus.py --corpus ../data/raw/Corpus_VF_Dominios.xlsx \
    --phishing-real ../data/raw/phishing_real.csv \
    --benign-real   ../data/raw/benign_real.csv --outdir ../data/raw
python3 build_dataset.py --phishing ../data/raw/phishing_all.csv \
    --benign ../data/raw/benign_all.csv \
    --out ../data/processed/dataset_combinado_host.csv --host-only
python3 train_baseline.py --data ../data/processed/dataset_combinado_host.csv --report ../reports/baseline_combinado.md
python3 ablation.py       --data ../data/processed/dataset_combinado_host.csv --report ../reports/ablacion_combinado.md
python3 eval_region.py    --data ../data/processed/dataset_combinado_host.csv \
    --regiones ../data/raw/corpus_regiones.csv --report ../reports/eval_region.md
```

**Resultado (CV 5-fold + hold-out 30%, seed 42):**

| Modelo | CV-F1 | Test F1 | ROC-AUC |
|--------|------:|--------:|--------:|
| Regresión Logística | 0.805 | 0.763 | 0.912 |
| Random Forest | 0.844 | 0.804 | 0.925 |

Números más bajos que el escenario OpenPhish/Tranco pero **más honestos**: el
dataset es 2× más grande y más difícil (phishing de muchas plataformas, no un
único feed), y la ablación muestra que la señal sobrevive al quitar TLD y largos
(config «solo señales de phishing»: RF AUC 0.907). No hay AUC perfecto ni atajo
de formato. Ver `baseline_combinado.md` y `ablacion_combinado.md`.

**Generalización a los casos uruguayos (lo central para el alcance regional):**
el detector entrenado sobre el corpus amplio **detecta 40 de los 42 casos UY
(recall 0.95)**, con predicción out-of-fold (cada host lo clasifica un modelo que
no lo vio). Solo se escapan dos apex minimalistas sin señal léxica
(`antel.gu.cc`, `trick.com.uy`), que necesitan señales externas (edad del dominio,
certificado, reputación DNS). Detalle en `eval_region.md`.

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
