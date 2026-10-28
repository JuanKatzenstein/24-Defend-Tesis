# Evaluación de sintéticos — `phishing_sintetico_llm_v4.csv`

## Veredicto

| chequeo | estado | criterio |
|---|:-:|---|
| Integridad | **OK** | sin formato inválido, sin hosts del dataset, sin fuga a valid/test |
| Fidelidad | **OK** | KS mediano 0.14 (objetivo <= 0.15) |
| Diversidad | **OK** | <= 5% casi-duplicados internos y <= 5% memorización de train |
| Firma | **REVISAR** | AUC n-gramas 0.83 (<= 0.75 OK, > 0.9 el generador deja firma) |
| Utilidad | **NO MEJORA** | PR-AUC test: real 0.8840 | control 0.8831 | sintético 0.8801 | moldes repetidos 0.8652 |

## 1. Integridad

- n: 206
- formato_invalido: 0
- duplicados_internos: 0
- en_dataset: 0
- casi_copia_dataset: 0
- fuga_lev1_valid_test: 0

## 2. Fidelidad (vs. phishing real de train)

Formas — real: {'apex': 0.404, 'sub_ajeno': 0.393, 'plataforma': 0.203} · sintético: {'apex': 0.529, 'sub_ajeno': 0.32, 'plataforma': 0.15}

| feature | media real | media sintético | KS |
|---|--:|--:|--:|
| host_len | 26.626 | 18.985 | 0.37 |
| host_entropy | 3.683 | 3.565 | 0.23 |
| digit_ratio | 0.036 | 0.007 | 0.22 |
| n_hyphens | 0.849 | 0.243 | 0.22 |
| n_digits | 1.119 | 0.117 | 0.22 |
| sld_len | 11.563 | 9.374 | 0.21 |
| ratio_consonantes | 0.620 | 0.642 | 0.20 |
| has_brand | 0.229 | 0.034 | 0.19 |
| brand_suplantada | 0.225 | 0.034 | 0.19 |
| letter_ratio | 0.866 | 0.897 | 0.17 |
| tld_sospechoso | 0.136 | 0.019 | 0.12 |
| sld_entropy | 2.816 | 2.787 | 0.11 |
| n_subdomains | 0.799 | 0.573 | 0.11 |
| n_dots | 1.799 | 1.573 | 0.11 |
| max_run_consonantes | 2.235 | 2.422 | 0.08 |
| en_plataforma_hosting | 0.203 | 0.150 | 0.05 |
| dist_marca_min | 2.763 | 2.869 | 0.05 |
| hex_largo | 0.013 | 0.000 | 0.01 |
| typosquat | 0.160 | 0.150 | 0.01 |
| n_palabras_gancho | 0.045 | 0.034 | 0.01 |

## 3. Diversidad

- casi_duplicados_internos: 0.019
- memorizacion_train: 0.005
- similitud_media_al_real_mas_cercano: 0.457

## 4. Firma (sintético vs. real)

- AUC n-gramas de caracteres: 0.835
- AUC features léxicas: 0.866
- n por clase: 206
- n-gramas que más delatan al sintético: x., .com, om, com, tr, t.c, t., z, .co, t.co, k, x, k., o, uv

## 5. Utilidad (Random Forest, test real, media de 5 semillas)

| experimento | PR-AUC | ±sd | ROC-AUC | recall @ FPR 1% | FPR en legítimos extra |
|---|--:|--:|--:|--:|--:|
| A: solo real | 0.8840 | 0.0014 | 0.9163 | 0.494 | 0.094 |
| B: real + 206 repetidos (control) | 0.8831 | 0.0031 | 0.9158 | 0.517 | 0.096 |
| C: real + 206 sintéticos | 0.8801 | 0.0020 | 0.9182 | 0.469 | 0.104 |
| D: real + 206 moldes difíciles repetidos (control) | 0.8652 | 0.0024 | 0.9140 | 0.461 | 0.092 |

FPR en legítimos extra = proporción de hosts de valid_uy y test_hosting (todos legítimos) marcados como phishing con umbral 0.5.
