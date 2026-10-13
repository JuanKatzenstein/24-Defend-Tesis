# Baseline — Detector de phishing en URLs

- Dataset: 2300 URLs (300 phishing / 2000 legit) · 30 features numéricas + TLD (one-hot)
- Split: 70% train / 30% test (estratificado, seed 42)
- CV: 5-fold estratificado sobre el train

> **Nota metodológica:** dataset chico y en parte sintético → métricas optimistas. Validan el pipeline, no son resultado final. Ampliar con feeds reales (PhishTank/OpenPhish) y ranking legítimo (Tranco) para los números definitivos.

### Regresión Logística

- CV F1 (train, 5-fold): 0.995 ± 0.006
- Test — accuracy 0.999 · precision 1.000 · recall 0.989 · F1 0.994 · ROC-AUC 1.000

Matriz de confusión (test) — filas=real, cols=pred [legit, phishing]:
```
            pred_legit  pred_phish
real_legit         600           0
real_phish           1          89
```

### Random Forest

- CV F1 (train, 5-fold): 1.000 ± 0.000
- Test — accuracy 1.000 · precision 1.000 · recall 1.000 · F1 1.000 · ROC-AUC 1.000

Matriz de confusión (test) — filas=real, cols=pred [legit, phishing]:
```
            pred_legit  pred_phish
real_legit         600           0
real_phish           0          90
```

### Importancia de features (Random Forest, top 15)

- path_len: 0.2095
- n_slash: 0.1981
- url_len: 0.1340
- n_dots: 0.0841
- host_len: 0.0681
- n_subdomains: 0.0608
- host_entropy: 0.0376
- n_digits: 0.0287
- n_hyphens: 0.0257
- digit_ratio: 0.0236
- en_plataforma_hosting: 0.0222
- https: 0.0174
- letter_ratio: 0.0149
- sld_len: 0.0129
- sld_entropy: 0.0095

