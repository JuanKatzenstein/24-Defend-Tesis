# Evaluación de sintéticos — `phishing_sintetico_llm.csv`

## Veredicto

| chequeo | estado | criterio |
|---|:-:|---|
| Integridad | **OK** | sin formato inválido, sin hosts del dataset, sin fuga a valid/test |
| Fidelidad | **OK** | KS mediano 0.10 (objetivo <= 0.15) |
| Diversidad | **OK** | <= 5% casi-duplicados internos y <= 5% memorización de train |
| Firma | **FALLA** | AUC n-gramas 0.98 (<= 0.75 OK, > 0.9 el generador deja firma) |
| Utilidad | **OK** | PR-AUC test: real 0.8840 | control 0.8791 | sintético 0.8856 |

## 1. Integridad

- n: 245
- formato_invalido: 0
- duplicados_internos: 0
- en_dataset: 0
- casi_copia_dataset: 0
- fuga_lev1_valid_test: 0

## 2. Fidelidad (vs. phishing real de train)

Formas — real: {'apex': 0.404, 'sub_ajeno': 0.393, 'plataforma': 0.203} · sintético: {'apex': 0.404, 'sub_ajeno': 0.376, 'plataforma': 0.22}

| feature | media real | media sintético | KS |
|---|--:|--:|--:|
| n_hyphens | 0.849 | 1.992 | 0.70 |
| sld_len | 11.563 | 16.996 | 0.46 |
| sld_entropy | 2.816 | 3.171 | 0.43 |
| host_len | 26.626 | 30.694 | 0.41 |
| n_palabras_gancho | 0.045 | 0.649 | 0.40 |
| letter_ratio | 0.866 | 0.869 | 0.37 |
| host_entropy | 3.683 | 3.823 | 0.34 |
| digit_ratio | 0.036 | 0.012 | 0.18 |
| n_digits | 1.119 | 0.355 | 0.17 |
| ratio_consonantes | 0.620 | 0.597 | 0.12 |
| n_subdomains | 0.799 | 0.661 | 0.07 |
| n_dots | 1.799 | 1.661 | 0.07 |
| max_run_consonantes | 2.235 | 2.086 | 0.07 |
| dist_marca_min | 2.763 | 2.616 | 0.06 |
| typosquat | 0.160 | 0.118 | 0.04 |
| en_plataforma_hosting | 0.203 | 0.220 | 0.02 |
| hex_largo | 0.013 | 0.000 | 0.01 |
| has_brand | 0.229 | 0.220 | 0.01 |
| tld_sospechoso | 0.136 | 0.143 | 0.01 |
| brand_suplantada | 0.225 | 0.220 | 0.00 |

## 3. Diversidad

- casi_duplicados_internos: 0.000
- memorizacion_train: 0.000
- similitud_media_al_real_mas_cercano: 0.325

## 4. Firma (sintético vs. real)

- AUC n-gramas de caracteres: 0.981
- AUC features léxicas: 0.979
- n por clase: 245
- n-gramas que más delatan al sintético: -, o-, a-, en, s-, nt, -o, -c, -p, ent, fi, os-, -v, e-, fic

## 5. Utilidad (Random Forest, test real, media de 5 semillas)

| experimento | PR-AUC | ±sd | ROC-AUC | recall @ FPR 1% | FPR en legítimos extra |
|---|--:|--:|--:|--:|--:|
| A: solo real | 0.8840 | 0.0014 | 0.9163 | 0.494 | 0.094 |
| B: real + 245 repetidos (control) | 0.8791 | 0.0025 | 0.9153 | 0.493 | 0.093 |
| C: real + 245 sintéticos | 0.8856 | 0.0010 | 0.9182 | 0.497 | 0.087 |

## 6. Utilidad con detector de n-gramas (TF-IDF 1-4 + regresión logística, test real)

| experimento | PR-AUC | ±sd | ROC-AUC | recall @ FPR 1% | FPR en legítimos extra |
|---|--:|--:|--:|--:|--:|
| A: solo real | 0.9165 | 0.0000 | 0.9325 | 0.728 | 0.027 |
| B: real + 245 repetidos (control) | 0.9133 | 0.0005 | 0.9297 | 0.726 | 0.025 |
| C: real + 245 sintéticos | 0.9163 | 0.0000 | 0.9322 | 0.746 | 0.027 |

FPR en legítimos extra = proporción de hosts de valid_uy y test_hosting (todos legítimos) marcados como phishing con umbral 0.5.
