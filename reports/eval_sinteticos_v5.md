# Evaluación de sintéticos — `phishing_sintetico_llm_v5.csv`

## Veredicto

| chequeo | estado | criterio |
|---|:-:|---|
| Integridad | **OK** | sin formato inválido, sin hosts del dataset, sin fuga a valid/test |
| Fidelidad | **OK** | KS mediano 0.13 (objetivo <= 0.15) |
| Diversidad | **OK** | <= 5% casi-duplicados internos y <= 5% memorización de train |
| Firma | **REVISAR** | AUC n-gramas 0.89 (<= 0.75 OK, > 0.9 el generador deja firma) |
| Utilidad | **NO MEJORA** | PR-AUC test: real 0.8840 | control 0.8816 | sintético 0.8752 | moldes repetidos 0.8763 |

## 1. Integridad

- n: 147
- formato_invalido: 0
- duplicados_internos: 0
- en_dataset: 0
- casi_copia_dataset: 0
- fuga_lev1_valid_test: 0

## 2. Fidelidad (vs. phishing real de train)

Formas — real: {'apex': 0.404, 'sub_ajeno': 0.393, 'plataforma': 0.203} · sintético: {'apex': 0.463, 'sub_ajeno': 0.333, 'plataforma': 0.204}

| feature | media real | media sintético | KS |
|---|--:|--:|--:|
| host_len | 26.626 | 20.850 | 0.31 |
| sld_len | 11.563 | 8.680 | 0.27 |
| letter_ratio | 0.866 | 0.900 | 0.26 |
| host_entropy | 3.683 | 3.566 | 0.26 |
| digit_ratio | 0.036 | 0.008 | 0.24 |
| n_digits | 1.119 | 0.143 | 0.22 |
| n_hyphens | 0.849 | 0.279 | 0.19 |
| sld_entropy | 2.816 | 2.566 | 0.16 |
| max_run_consonantes | 2.235 | 2.007 | 0.16 |
| tld_sospechoso | 0.136 | 0.000 | 0.14 |
| has_brand | 0.229 | 0.109 | 0.12 |
| brand_suplantada | 0.225 | 0.109 | 0.12 |
| ratio_consonantes | 0.620 | 0.610 | 0.10 |
| dist_marca_min | 2.763 | 2.912 | 0.09 |
| typosquat | 0.160 | 0.102 | 0.06 |
| n_dots | 1.799 | 1.673 | 0.04 |
| n_subdomains | 0.799 | 0.673 | 0.04 |
| n_palabras_gancho | 0.045 | 0.020 | 0.02 |
| hex_largo | 0.013 | 0.000 | 0.01 |
| en_plataforma_hosting | 0.203 | 0.204 | 0.00 |

## 3. Diversidad

- casi_duplicados_internos: 0.000
- memorizacion_train: 0.007
- similitud_media_al_real_mas_cercano: 0.536

## 4. Firma (sintético vs. real)

- AUC n-gramas de caracteres: 0.886
- AUC features léxicas: 0.906
- n por clase: 147
- n-gramas que más delatan al sintético: agal, gal, maga, aga, mag, alu, galu, ga, a, lu, ma, m, om, .com, com

## 5. Utilidad (Random Forest, test real, media de 5 semillas)

| experimento | PR-AUC | ±sd | ROC-AUC | recall @ FPR 1% | FPR en legítimos extra |
|---|--:|--:|--:|--:|--:|
| A: solo real | 0.8840 | 0.0014 | 0.9163 | 0.494 | 0.094 |
| B: real + 147 repetidos (control) | 0.8816 | 0.0010 | 0.9155 | 0.481 | 0.093 |
| C: real + 147 sintéticos | 0.8752 | 0.0021 | 0.9178 | 0.456 | 0.105 |
| D: real + 147 moldes difíciles repetidos (control) | 0.8763 | 0.0026 | 0.9159 | 0.468 | 0.089 |

## 6. Utilidad con detector de n-gramas (TF-IDF 1-4 + regresión logística, test real)

| experimento | PR-AUC | ±sd | ROC-AUC | recall @ FPR 1% | FPR en legítimos extra |
|---|--:|--:|--:|--:|--:|
| A: solo real | 0.9165 | 0.0000 | 0.9325 | 0.728 | 0.027 |
| B: real + 147 repetidos (control) | 0.9144 | 0.0004 | 0.9305 | 0.724 | 0.026 |
| C: real + 147 sintéticos | 0.9173 | 0.0000 | 0.9332 | 0.731 | 0.026 |
| D: real + 147 moldes difíciles repetidos (control) | 0.9169 | 0.0004 | 0.9331 | 0.731 | 0.027 |

FPR en legítimos extra = proporción de hosts de valid_uy y test_hosting (todos legítimos) marcados como phishing con umbral 0.5.
