# 24-Defend-Tesis — Detección de phishing en URLs/dominios

Pipeline para una tesis de **detección** de phishing a partir de la cadena de la
URL/host (clasificación *antes* de visitar el sitio). El foco es defensivo:
análisis del corpus, extracción de features interpretables, y entrenamiento +
evaluación honesta de un detector.

## Estructura

```
data/raw/         corpus de entrada (phishing) y clase legítima (semilla)
data/processed/   dataset etiquetado + features
reports/          reportes de evaluación
src/
  features.py        extracción de features léxicas de URL/host (32 features)
  make_benign.py     construye la clase negativa (legítimas + hard negatives)
  build_dataset.py   une phishing + legítimas y extrae features
  train_baseline.py  baseline interpretable (LogReg + Random Forest)
  ablation.py        ablación de features (señal real vs. fuga)
  ingest_real.py     ingesta de feeds reales (OpenPhish/PhishTank + Tranco)
tools/
  plan_lote.py       Fase 2: muestreo estadístico de parámetros del corpus
  validar_lote.py    Fase 3: valida el plan (proporciones + no-repetición)
```

## Cómo correr

```bash
cd src
python3 make_benign.py   --n 60 --out ../data/raw/benign_seed.csv --seed 42
python3 build_dataset.py --phishing ../data/raw/corpus_sintetico.csv \
                         --benign   ../data/raw/benign_seed.csv \
                         --out      ../data/processed/dataset.csv
python3 train_baseline.py --data ../data/processed/dataset.csv --report ../reports/baseline.md
python3 ablation.py       --data ../data/processed/dataset.csv --report ../reports/ablacion.md
```

### Datos reales (resultado principal)

```bash
cd src
# descarga feeds reales (requiere red saliente a openphish.com y tranco-list.eu)
python3 ingest_real.py --phishing-url https://openphish.com/feed.txt \
                       --tranco-url https://tranco-list.eu/top-1m.csv.zip \
                       --n-benign 2000 --outdir ../data/raw
# evaluación a nivel DOMINIO (evita el artefacto de formato de Tranco sin paths)
python3 build_dataset.py --phishing ../data/raw/phishing_real.csv \
                         --benign ../data/raw/benign_real.csv \
                         --out ../data/processed/dataset_real_host.csv --host-only
python3 train_baseline.py --data ../data/processed/dataset_real_host.csv --report ../reports/baseline_real_host.md
python3 ablation.py       --data ../data/processed/dataset_real_host.csv --report ../reports/ablacion_real_host.md
python3 curvas_eval.py    --data ../data/processed/dataset_real_host.csv --outdir ../reports/real
```

Resultado: **ROC-AUC ~0.97, F1 ~0.90** (OpenPhish vs Tranco), robusto a la ablación.
Ver **`reports/RESULTADOS.md`** para el resumen completo.

### Reportes

- `reports/RESULTADOS.md` — **resumen principal** (sintético + datos reales).
- `reports/baseline*.md` — métricas del baseline (LogReg + Random Forest).
- `reports/ablacion*.md` — ablación de features (señal real vs. fuga).
- `reports/analisis_errores.md` — errores del detector en validación cruzada.
- `reports/real/` — curvas ROC/PR y umbral sobre datos reales.

## Notas metodológicas (importantes para defender la tesis)

1. **Las métricas actuales son optimistas y NO son resultado final.** El dataset
   es chico (80 URLs) y la clase legítima es una semilla construida con dominios
   oficiales reales. En el baseline, el Random Forest llega a métricas perfectas
   apoyándose en atajos como el TLD (`.uy` ≈ legítimo): es **fuga de
   información**, no capacidad de detección. Sirve para validar que el pipeline
   funciona de punta a punta, nada más.

   - **Mitigación aplicada:** la clase negativa incluye *hard negatives* — URLs
     legítimas reales que parecen sospechosas (logins como
     `login.microsoftonline.com`, sitios en `vercel.app`/`github.io`, empresas en
     `.xyz`/`.io`, URLs largas con query/hash, acortadores). Con eso el AUC perfecto
     del baseline inicial bajó a ~0.96–0.99 y aparecieron errores estructurales
     reales (ver `reports/analisis_errores.md`).

2. **Para números defendibles, usar datos reales:**
   - Positivos (phishing): PhishTank, OpenPhish, APWG, datasets de Mendeley/UCI.
   - Negativos (legítimos): ranking real tipo Tranco / Majestic Million.
   - El `corpus_sintetico.csv` regional queda como *caso de estudio* ilustrativo,
     no como el train/test principal.

3. **Controlar fugas de distribución:** evitar que el modelo separe las clases por
   artefactos del armado del dataset (p. ej. TLD, longitud sistemáticamente
   distinta). Conviene reportar también una evaluación con features "neutralizadas"
   y/o un split temporal.

## Hallazgos del validador (Fase 3)

Al validar un lote generado por `plan_lote.py`, la Fase 3 detectó que las
combinaciones `(marca, gramática)` pueden repetirse para gramáticas que *fuerzan*
la marca (p. ej. `S1b`→`sucive`, `S3`→`brou`): el control de no-repetición en
`armar_lote()` se hace sobre la marca sorteada, pero `fila()` la reescribe después,
así que el dedup no cubre esos casos. Es justamente lo que un validador debe cazar.
Queda documentado como defecto conocido del generador (no se modificó la Fase 2).

## Alcance

Este repo cubre **solo el lado de detección/defensa**. No incluye generación de
hostnames de phishing desplegables. El script `plan_lote.py` (muestreo estadístico
de parámetros) se mantiene aparte como herramienta de análisis del corpus.
