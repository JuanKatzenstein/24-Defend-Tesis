# Ablación de features — ¿señal real o fuga?

Dataset: 111 URLs (20 phishing / 91 legit) · CV 5-fold · hold-out 30% · seed 42

Cada config quita features. Si al pasar de A a B/C/D el rendimiento cae mucho, el modelo dependía de un atajo (TLD, largos). Lo que sobrevive es la señal defendible.

| Config | LogReg CV-F1 | LogReg test-F1 | LogReg AUC | RF CV-F1 | RF test-F1 | RF AUC |
|--------|------|------|------|------|------|------|
| A. full (todo + TLD one-hot) | 0.725±0.129 | 0.833 | 0.994 | 0.791±0.163 | 0.909 | 0.994 |
| B. sin TLD one-hot | 0.691±0.158 | 0.833 | 0.994 | 0.671±0.185 | 0.909 | 0.994 |
| C. sin TLD ni largos | 0.682±0.202 | 0.923 | 0.994 | 0.860±0.196 | 0.833 | 0.994 |
| D. solo señales de phishing | 0.611±0.365 | 0.857 | 1.000 | 0.810±0.247 | 0.833 | 0.964 |

**Lectura:** la config D («solo señales de phishing») es la más honesta — usa features que describen el *mecanismo* del phishing (TLD sospechoso, hosting gratuito, marca suplantada, palabras-gancho, entropía del dominio) y no artefactos del armado del dataset.
