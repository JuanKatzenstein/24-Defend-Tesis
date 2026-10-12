# Ablación de features — ¿señal real o fuga?

Dataset: 111 URLs (20 phishing / 91 legit) · CV 5-fold · hold-out 30% · seed 42

Cada config quita features. Si al pasar de A a B/C/D el rendimiento cae mucho, el modelo dependía de un atajo (TLD, largos). Lo que sobrevive es la señal defendible.

| Config | LogReg CV-F1 | LogReg test-F1 | LogReg AUC | RF CV-F1 | RF test-F1 | RF AUC |
|--------|------|------|------|------|------|------|
| A. full (todo + TLD one-hot) | 0.725±0.129 | 0.833 | 0.994 | 0.791±0.163 | 0.909 | 0.988 |
| B. sin TLD one-hot | 0.725±0.129 | 0.833 | 0.988 | 0.800±0.219 | 0.909 | 0.994 |
| C. sin TLD ni largos | 0.753±0.165 | 0.923 | 0.994 | 0.860±0.196 | 0.833 | 0.994 |
| D. solo señales de phishing | 0.748±0.224 | 0.857 | 0.994 | 0.783±0.203 | 0.833 | 0.964 |

**Lectura:** la config D («solo señales de phishing») es la más honesta — usa features que describen el *mecanismo* del phishing (TLD sospechoso, hosting gratuito, marca suplantada, palabras-gancho, entropía del dominio) y no artefactos del armado del dataset.
