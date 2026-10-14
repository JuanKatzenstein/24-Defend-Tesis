# Baseline — Detector de phishing en URLs

- Dataset: 4633 URLs (1440 phishing / 3193 legit) · 30 features numéricas + TLD (one-hot)
- Split: 70% train / 30% test (estratificado, seed 42)
- CV: 5-fold estratificado sobre el train

> **Nota metodológica:** revisar siempre las *importancias* de features para descartar fugas por el armado del dataset (p. ej. formato de la clase negativa). Si la clase legítima son dominios pelados (Tranco), evaluar a nivel dominio (`--host-only`) para evitar que `path_len`/`n_slash` separen por formato en vez de por phishing. Contrastar con `ablation.py`: si el rendimiento no cae al quitar largos/TLD, la señal es real.

### Regresión Logística

- CV F1 (train, 5-fold): 0.805 ± 0.009
- Test — accuracy 0.847 · precision 0.737 · recall 0.792 · F1 0.763 · ROC-AUC 0.912

Matriz de confusión (test) — filas=real, cols=pred [legit, phishing]:
```
            pred_legit  pred_phish
real_legit         836         122
real_phish          90         342
```

### Random Forest

- CV F1 (train, 5-fold): 0.844 ± 0.014
- Test — accuracy 0.878 · precision 0.805 · recall 0.803 · F1 0.804 · ROC-AUC 0.925

Matriz de confusión (test) — filas=real, cols=pred [legit, phishing]:
```
            pred_legit  pred_phish
real_legit         874          84
real_phish          85         347
```

### Importancia de features (Random Forest, top 15)

- url_len: 0.1253
- host_len: 0.1189
- host_entropy: 0.1061
- sld_entropy: 0.0678
- sld_len: 0.0646
- ratio_consonantes: 0.0620
- letter_ratio: 0.0521
- n_hyphens: 0.0462
- max_run_consonantes: 0.0382
- n_subdomains: 0.0283
- n_dots: 0.0271
- en_plataforma_hosting: 0.0229
- digit_ratio: 0.0210
- tld_sospechoso: 0.0203
- has_brand: 0.0201

