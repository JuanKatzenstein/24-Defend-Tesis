# Baseline — Detector de phishing en URLs

- Dataset: 2285 URLs (286 phishing / 1999 legit) · 30 features numéricas + TLD (one-hot)
- Split: 70% train / 30% test (estratificado, seed 42)
- CV: 5-fold estratificado sobre el train

> **Nota metodológica:** revisar siempre las *importancias* de features para descartar fugas por el armado del dataset (p. ej. formato de la clase negativa). Si la clase legítima son dominios pelados (Tranco), evaluar a nivel dominio (`--host-only`) para evitar que `path_len`/`n_slash` separen por formato en vez de por phishing. Contrastar con `ablation.py`: si el rendimiento no cae al quitar largos/TLD, la señal es real.

### Regresión Logística

- CV F1 (train, 5-fold): 0.883 ± 0.019
- Test — accuracy 0.977 · precision 0.880 · recall 0.942 · F1 0.910 · ROC-AUC 0.974

Matriz de confusión (test) — filas=real, cols=pred [legit, phishing]:
```
            pred_legit  pred_phish
real_legit         589          11
real_phish           5          81
```

### Random Forest

- CV F1 (train, 5-fold): 0.887 ± 0.043
- Test — accuracy 0.975 · precision 0.916 · recall 0.884 · F1 0.899 · ROC-AUC 0.987

Matriz de confusión (test) — filas=real, cols=pred [legit, phishing]:
```
            pred_legit  pred_phish
real_legit         593           7
real_phish          10          76
```

### Importancia de features (Random Forest, top 15)

- url_len: 0.1461
- n_dots: 0.1367
- host_len: 0.1310
- n_subdomains: 0.1161
- host_entropy: 0.0790
- https: 0.0407
- n_hyphens: 0.0400
- sld_entropy: 0.0328
- en_plataforma_hosting: 0.0304
- sld_len: 0.0297
- letter_ratio: 0.0291
- ratio_consonantes: 0.0286
- max_run_consonantes: 0.0230
- digit_ratio: 0.0217
- n_digits: 0.0154

