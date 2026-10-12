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
  features.py        extracción de features léxicas de URL/host (28 features)
  make_benign.py     construye la clase negativa (URLs legítimas reales)
  build_dataset.py   une phishing + legítimas y extrae features
  train_baseline.py  baseline interpretable (LogReg + Random Forest)
```

## Cómo correr

```bash
cd src
python3 make_benign.py   --n 60 --out ../data/raw/benign_seed.csv --seed 42
python3 build_dataset.py --phishing ../data/raw/corpus_sintetico.csv \
                         --benign   ../data/raw/benign_seed.csv \
                         --out      ../data/processed/dataset.csv
python3 train_baseline.py --data ../data/processed/dataset.csv --report ../reports/baseline.md
```

## Notas metodológicas (importantes para defender la tesis)

1. **Las métricas actuales son optimistas y NO son resultado final.** El dataset
   es chico (80 URLs) y la clase legítima es una semilla construida con dominios
   oficiales reales. En el baseline, el Random Forest llega a métricas perfectas
   apoyándose en atajos como el TLD (`.uy` ≈ legítimo): es **fuga de
   información**, no capacidad de detección. Sirve para validar que el pipeline
   funciona de punta a punta, nada más.

2. **Para números defendibles, usar datos reales:**
   - Positivos (phishing): PhishTank, OpenPhish, APWG, datasets de Mendeley/UCI.
   - Negativos (legítimos): ranking real tipo Tranco / Majestic Million.
   - El `corpus_sintetico.csv` regional queda como *caso de estudio* ilustrativo,
     no como el train/test principal.

3. **Controlar fugas de distribución:** evitar que el modelo separe las clases por
   artefactos del armado del dataset (p. ej. TLD, longitud sistemáticamente
   distinta). Conviene reportar también una evaluación con features "neutralizadas"
   y/o un split temporal.

## Alcance

Este repo cubre **solo el lado de detección/defensa**. No incluye generación de
hostnames de phishing desplegables. El script `plan_lote.py` (muestreo estadístico
de parámetros) se mantiene aparte como herramienta de análisis del corpus.
