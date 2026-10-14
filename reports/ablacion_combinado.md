# Ablación de features — ¿señal real o fuga?

Dataset: 4633 URLs (1440 phishing / 3193 legit) · CV 5-fold · hold-out 30% · seed 42

Cada config quita features. Si al pasar de A a B/C/D el rendimiento cae mucho, el modelo dependía de un atajo (TLD, largos). Lo que sobrevive es la señal defendible.

| Config | LogReg CV-F1 | LogReg test-F1 | LogReg AUC | RF CV-F1 | RF test-F1 | RF AUC |
|--------|------|------|------|------|------|------|
| A. full (todo + TLD one-hot) | 0.805±0.009 | 0.763 | 0.912 | 0.844±0.014 | 0.804 | 0.925 |
| B. sin TLD one-hot | 0.774±0.012 | 0.746 | 0.897 | 0.819±0.017 | 0.793 | 0.920 |
| C. sin TLD ni largos | 0.771±0.012 | 0.737 | 0.894 | 0.826±0.021 | 0.798 | 0.918 |
| D. solo señales de phishing | 0.720±0.008 | 0.703 | 0.873 | 0.812±0.008 | 0.778 | 0.907 |

**Lectura:** la config D («solo señales de phishing») es la más honesta — usa features que describen el *mecanismo* del phishing (TLD sospechoso, hosting gratuito, marca suplantada, palabras-gancho, entropía del dominio) y no artefactos del armado del dataset.
