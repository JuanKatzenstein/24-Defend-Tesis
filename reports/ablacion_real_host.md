# Ablación de features — ¿señal real o fuga?

Dataset: 2285 URLs (286 phishing / 1999 legit) · CV 5-fold · hold-out 30% · seed 42

Cada config quita features. Si al pasar de A a B/C/D el rendimiento cae mucho, el modelo dependía de un atajo (TLD, largos). Lo que sobrevive es la señal defendible.

| Config | LogReg CV-F1 | LogReg test-F1 | LogReg AUC | RF CV-F1 | RF test-F1 | RF AUC |
|--------|------|------|------|------|------|------|
| A. full (todo + TLD one-hot) | 0.883±0.019 | 0.910 | 0.974 | 0.887±0.043 | 0.899 | 0.987 |
| B. sin TLD one-hot | 0.876±0.019 | 0.895 | 0.974 | 0.883±0.030 | 0.851 | 0.985 |
| C. sin TLD ni largos | 0.867±0.021 | 0.901 | 0.974 | 0.895±0.032 | 0.926 | 0.984 |
| D. solo señales de phishing | 0.811±0.040 | 0.863 | 0.969 | 0.860±0.043 | 0.880 | 0.982 |

**Lectura:** la config D («solo señales de phishing») es la más honesta — usa features que describen el *mecanismo* del phishing (TLD sospechoso, hosting gratuito, marca suplantada, palabras-gancho, entropía del dominio) y no artefactos del armado del dataset.
