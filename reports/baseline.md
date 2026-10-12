# Baseline — Detector de phishing en URLs

- Dataset: 80 URLs (20 phishing / 60 legit) · 26 features numéricas + TLD (one-hot)
- Split: 70% train / 30% test (estratificado, seed 42)
- CV: 5-fold estratificado sobre el train

> **Nota metodológica:** dataset chico y en parte sintético → métricas optimistas. Validan el pipeline, no son resultado final. Ampliar con feeds reales (PhishTank/OpenPhish) y ranking legítimo (Tranco) para los números definitivos.

### Regresión Logística

- CV F1 (train, 5-fold): 0.831 ± 0.183
- Test — accuracy 0.958 · precision 1.000 · recall 0.833 · F1 0.909 · ROC-AUC 1.000

Matriz de confusión (test) — filas=real, cols=pred [legit, phishing]:
```
            pred_legit  pred_phish
real_legit          18           0
real_phish           1           5
```

### Random Forest

- CV F1 (train, 5-fold): 0.871 ± 0.194
- Test — accuracy 1.000 · precision 1.000 · recall 1.000 · F1 1.000 · ROC-AUC 1.000

Matriz de confusión (test) — filas=real, cols=pred [legit, phishing]:
```
            pred_legit  pred_phish
real_legit          18           0
real_phish           0           6
```

### Importancia de features (Random Forest, top 15)

- sld_entropy: 0.1668
- host_len: 0.1096
- host_entropy: 0.0961
- sld_len: 0.0906
- path_len: 0.0885
- url_len: 0.0738
- tld_uy: 0.0722
- n_slash: 0.0456
- n_subdomains: 0.0364
- n_dots: 0.0357
- en_plataforma_hosting: 0.0286
- n_digits: 0.0279
- n_hyphens: 0.0242
- digit_ratio: 0.0183
- tld_com: 0.0155

