# Baseline — Detector de phishing en URLs

- Dataset: 111 URLs (20 phishing / 91 legit) · 26 features numéricas + TLD (one-hot)
- Split: 70% train / 30% test (estratificado, seed 42)
- CV: 5-fold estratificado sobre el train

> **Nota metodológica:** dataset chico y en parte sintético → métricas optimistas. Validan el pipeline, no son resultado final. Ampliar con feeds reales (PhishTank/OpenPhish) y ranking legítimo (Tranco) para los números definitivos.

### Regresión Logística

- CV F1 (train, 5-fold): 0.725 ± 0.129
- Test — accuracy 0.941 · precision 0.833 · recall 0.833 · F1 0.833 · ROC-AUC 0.994

Matriz de confusión (test) — filas=real, cols=pred [legit, phishing]:
```
            pred_legit  pred_phish
real_legit          27           1
real_phish           1           5
```

### Random Forest

- CV F1 (train, 5-fold): 0.791 ± 0.163
- Test — accuracy 0.971 · precision 1.000 · recall 0.833 · F1 0.909 · ROC-AUC 0.988

Matriz de confusión (test) — filas=real, cols=pred [legit, phishing]:
```
            pred_legit  pred_phish
real_legit          28           0
real_phish           1           5
```

### Importancia de features (Random Forest, top 15)

- sld_entropy: 0.1582
- host_entropy: 0.1162
- sld_len: 0.1119
- path_len: 0.0994
- host_len: 0.0840
- n_slash: 0.0742
- tld_uy: 0.0507
- url_len: 0.0425
- en_plataforma_hosting: 0.0344
- n_dots: 0.0281
- digit_ratio: 0.0275
- n_digits: 0.0266
- n_subdomains: 0.0236
- letter_ratio: 0.0225
- tld_co: 0.0168

