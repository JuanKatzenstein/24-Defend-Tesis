# Evaluación de sintéticos — `phishing_sintetico_llm_v2.csv`

## Veredicto

| chequeo | estado | criterio |
|---|:-:|---|
| Integridad | **OK** | sin formato inválido, sin hosts del dataset, sin fuga a valid/test |
| Fidelidad | **OK** | KS mediano 0.06 (objetivo <= 0.15) |
| Diversidad | **OK** | <= 5% casi-duplicados internos y <= 5% memorización de train |
| Firma | **FALLA** | AUC n-gramas 0.92 (<= 0.75 OK, > 0.9 el generador deja firma) |
| Utilidad | **OK** | PR-AUC test: real 0.8840 | control 0.8825 | sintético 0.8865 |

## 1. Integridad

- n: 224
- formato_invalido: 0
- duplicados_internos: 0
- en_dataset: 0
- casi_copia_dataset: 0
- fuga_lev1_valid_test: 0

## 2. Fidelidad (vs. phishing real de train)

Formas — real: {'apex': 0.404, 'sub_ajeno': 0.393, 'plataforma': 0.203} · sintético: {'apex': 0.371, 'sub_ajeno': 0.353, 'plataforma': 0.277}

| feature | media real | media sintético | KS |
|---|--:|--:|--:|
| ratio_consonantes | 0.620 | 0.620 | 0.16 |
| sld_entropy | 2.816 | 2.935 | 0.12 |
| n_palabras_gancho | 0.045 | 0.196 | 0.10 |
| letter_ratio | 0.866 | 0.853 | 0.08 |
| n_hyphens | 0.849 | 1.085 | 0.08 |
| max_run_consonantes | 2.235 | 2.080 | 0.08 |
| en_plataforma_hosting | 0.203 | 0.277 | 0.07 |
| host_entropy | 3.683 | 3.719 | 0.07 |
| digit_ratio | 0.036 | 0.043 | 0.07 |
| host_len | 26.626 | 25.942 | 0.07 |
| sld_len | 11.563 | 11.670 | 0.06 |
| n_digits | 1.119 | 1.397 | 0.06 |
| n_subdomains | 0.799 | 0.754 | 0.04 |
| n_dots | 1.799 | 1.754 | 0.04 |
| has_brand | 0.229 | 0.192 | 0.04 |
| brand_suplantada | 0.225 | 0.192 | 0.03 |
| dist_marca_min | 2.763 | 2.674 | 0.03 |
| typosquat | 0.160 | 0.152 | 0.01 |
| tld_sospechoso | 0.136 | 0.129 | 0.01 |
| hex_largo | 0.013 | 0.018 | 0.00 |

## 3. Diversidad

- casi_duplicados_internos: 0.018
- memorizacion_train: 0.004
- similitud_media_al_real_mas_cercano: 0.339

## 4. Firma (sintético vs. real)

- AUC n-gramas de caracteres: 0.918
- AUC features léxicas: 0.788
- n por clase: 224
- n-gramas que más delatan al sintético: v, ces, -s, ve, as., ce, o, ac, s, ven, so, ace, vo, nas., 9

## 5. Utilidad (Random Forest, test real, media de 5 semillas)

| experimento | PR-AUC | ±sd | ROC-AUC | recall @ FPR 1% | FPR en legítimos extra |
|---|--:|--:|--:|--:|--:|
| A: solo real | 0.8840 | 0.0014 | 0.9163 | 0.494 | 0.094 |
| B: real + 224 repetidos (control) | 0.8825 | 0.0012 | 0.9163 | 0.508 | 0.096 |
| C: real + 224 sintéticos | 0.8865 | 0.0008 | 0.9224 | 0.473 | 0.096 |

FPR en legítimos extra = proporción de hosts de valid_uy y test_hosting (todos legítimos) marcados como phishing con umbral 0.5.
