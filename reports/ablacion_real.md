# Ablación de features — ¿señal real o fuga?

Dataset: 2300 URLs (300 phishing / 2000 legit) · CV 5-fold · hold-out 30% · seed 42

Cada config quita features. Si al pasar de A a B/C/D el rendimiento cae mucho, el modelo dependía de un atajo (TLD, largos). Lo que sobrevive es la señal defendible.

| Config | LogReg CV-F1 | LogReg test-F1 | LogReg AUC | RF CV-F1 | RF test-F1 | RF AUC |
|--------|------|------|------|------|------|------|
| A. full (todo + TLD one-hot) | 0.995±0.006 | 0.994 | 1.000 | 1.000±0.000 | 1.000 | 1.000 |
| B. sin TLD one-hot | 0.995±0.006 | 0.994 | 1.000 | 1.000±0.000 | 1.000 | 1.000 |
| C. sin TLD ni largos | 0.995±0.006 | 1.000 | 1.000 | 1.000±0.000 | 1.000 | 1.000 |
| D. solo señales de phishing | 0.893±0.029 | 0.896 | 0.970 | 0.926±0.030 | 0.899 | 0.986 |

**Lectura:** la config D («solo señales de phishing») es la más honesta — usa features que describen el *mecanismo* del phishing (TLD sospechoso, hosting gratuito, marca suplantada, palabras-gancho, entropía del dominio) y no artefactos del armado del dataset.
