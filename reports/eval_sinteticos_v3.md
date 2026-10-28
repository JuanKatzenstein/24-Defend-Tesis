# Evaluación de sintéticos — `phishing_sintetico_llm_v3.csv`

## Veredicto

| chequeo | estado | criterio |
|---|:-:|---|
| Integridad | **OK** | sin formato inválido, sin hosts del dataset, sin fuga a valid/test |
| Fidelidad | **OK** | KS mediano 0.05 (objetivo <= 0.15) |
| Diversidad | **OK** | <= 5% casi-duplicados internos y <= 5% memorización de train |
| Firma | **OK** | AUC n-gramas 0.63 (<= 0.75 OK, > 0.9 el generador deja firma) |
| Utilidad | **NO MEJORA** | PR-AUC test: real 0.8840 | control 0.8824 | sintético 0.8824 |

## 1. Integridad

- n: 208
- formato_invalido: 0
- duplicados_internos: 0
- en_dataset: 0
- casi_copia_dataset: 0
- fuga_lev1_valid_test: 0

## 2. Fidelidad (vs. phishing real de train)

Formas — real: {'apex': 0.404, 'sub_ajeno': 0.393, 'plataforma': 0.203} · sintético: {'apex': 0.409, 'sub_ajeno': 0.327, 'plataforma': 0.264}

| feature | media real | media sintético | KS |
|---|--:|--:|--:|
| ratio_consonantes | 0.620 | 0.636 | 0.08 |
| host_entropy | 3.683 | 3.732 | 0.08 |
| sld_len | 11.563 | 11.163 | 0.07 |
| en_plataforma_hosting | 0.203 | 0.264 | 0.06 |
| digit_ratio | 0.036 | 0.028 | 0.06 |
| sld_entropy | 2.816 | 2.800 | 0.06 |
| n_digits | 1.119 | 0.952 | 0.06 |
| n_hyphens | 0.849 | 0.904 | 0.05 |
| letter_ratio | 0.866 | 0.872 | 0.05 |
| host_len | 26.626 | 26.538 | 0.05 |
| n_palabras_gancho | 0.045 | 0.096 | 0.04 |
| max_run_consonantes | 2.235 | 2.409 | 0.04 |
| dist_marca_min | 2.763 | 2.784 | 0.03 |
| typosquat | 0.160 | 0.183 | 0.02 |
| hex_largo | 0.013 | 0.000 | 0.01 |
| has_brand | 0.229 | 0.216 | 0.01 |
| brand_suplantada | 0.225 | 0.216 | 0.01 |
| n_dots | 1.799 | 1.788 | 0.01 |
| n_subdomains | 0.799 | 0.788 | 0.01 |
| tld_sospechoso | 0.136 | 0.130 | 0.01 |

## 3. Diversidad

- casi_duplicados_internos: 0.000
- memorizacion_train: 0.005
- similitud_media_al_real_mas_cercano: 0.486

## 4. Firma (sintético vs. real)

- AUC n-gramas de caracteres: 0.626
- AUC features léxicas: 0.504
- n por clase: 208
- n-gramas que más delatan al sintético: con, nt, k, v, cc, cont, os, we, web, z., acc, ont, ces, l., eb.

## 5. Utilidad (Random Forest, test real, media de 5 semillas)

| experimento | PR-AUC | ±sd | ROC-AUC | recall @ FPR 1% | FPR en legítimos extra |
|---|--:|--:|--:|--:|--:|
| A: solo real | 0.8840 | 0.0014 | 0.9163 | 0.494 | 0.094 |
| B: real + 208 repetidos (control) | 0.8824 | 0.0022 | 0.9154 | 0.502 | 0.094 |
| C: real + 208 sintéticos | 0.8824 | 0.0008 | 0.9184 | 0.498 | 0.105 |

## 6. Utilidad con detector de n-gramas (TF-IDF 1-4 + regresión logística, test real)

| experimento | PR-AUC | ±sd | ROC-AUC | recall @ FPR 1% | FPR en legítimos extra |
|---|--:|--:|--:|--:|--:|
| A: solo real | 0.9165 | 0.0000 | 0.9325 | 0.728 | 0.027 |
| B: real + 208 repetidos (control) | 0.9139 | 0.0007 | 0.9302 | 0.723 | 0.025 |
| C: real + 208 sintéticos | 0.9166 | 0.0000 | 0.9325 | 0.728 | 0.033 |

FPR en legítimos extra = proporción de hosts de valid_uy y test_hosting (todos legítimos) marcados como phishing con umbral 0.5.
