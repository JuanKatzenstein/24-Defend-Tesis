# Evaluación de sintéticos — piloto de mutaciones (300, generado con generar_sinteticos_integral.py)

## Veredicto

| chequeo | estado | criterio |
|---|:-:|---|
| Integridad | **OK** | sin formato inválido, sin hosts del dataset, sin fuga a valid/test |
| Fidelidad | **OK** | KS mediano 0.06 (objetivo <= 0.15) |
| Diversidad | **REVISAR** | <= 5% casi-duplicados internos y <= 5% memorización de train |
| Firma | **REVISAR** | AUC n-gramas 0.75 (<= 0.75 OK, > 0.9 el generador deja firma) |
| Utilidad | **NO MEJORA** | PR-AUC test: real 0.8840 | control 0.8733 | sintético 0.8756 |

## 1. Integridad

- n: 300
- formato_invalido: 0
- duplicados_internos: 0
- en_dataset: 0
- casi_copia_dataset: 0
- fuga_lev1_valid_test: 0

## 2. Fidelidad (vs. phishing real de train)

Formas — real: {'apex': 0.404, 'sub_ajeno': 0.393, 'plataforma': 0.203} · sintético: {'apex': 0.53, 'sub_ajeno': 0.28, 'plataforma': 0.19}

| feature | media real | media sintético | KS |
|---|--:|--:|--:|
| n_dots | 1.799 | 1.573 | 0.11 |
| n_subdomains | 0.799 | 0.573 | 0.11 |
| has_brand | 0.229 | 0.120 | 0.11 |
| letter_ratio | 0.866 | 0.882 | 0.11 |
| brand_suplantada | 0.225 | 0.120 | 0.11 |
| host_len | 26.626 | 25.140 | 0.09 |
| host_entropy | 3.683 | 3.646 | 0.07 |
| digit_ratio | 0.036 | 0.025 | 0.07 |
| n_digits | 1.119 | 0.787 | 0.07 |
| sld_len | 11.563 | 12.210 | 0.06 |
| sld_entropy | 2.816 | 2.883 | 0.06 |
| ratio_consonantes | 0.620 | 0.625 | 0.06 |
| dist_marca_min | 2.763 | 2.920 | 0.06 |
| max_run_consonantes | 2.235 | 2.283 | 0.05 |
| n_hyphens | 0.849 | 0.817 | 0.03 |
| n_palabras_gancho | 0.045 | 0.010 | 0.03 |
| typosquat | 0.160 | 0.137 | 0.02 |
| tld_sospechoso | 0.136 | 0.157 | 0.02 |
| hex_largo | 0.013 | 0.000 | 0.01 |
| en_plataforma_hosting | 0.203 | 0.190 | 0.01 |

## 3. Diversidad

- casi_duplicados_internos: 0.057
- memorizacion_train: 0.217
- similitud_media_al_real_mas_cercano: 0.813

## 4. Firma (sintético vs. real)

- AUC n-gramas de caracteres: 0.751
- AUC features léxicas: 0.710
- n por clase: 300
- n-gramas que más delatan al sintético: aa, al, be, x, al., ae, al.c, l-, rr, ob, 5.c, 5.co, b, tal, u

## 5. Utilidad (Random Forest, test real, media de 5 semillas)

| experimento | PR-AUC | ±sd | ROC-AUC | recall @ FPR 1% | FPR en legítimos extra |
|---|--:|--:|--:|--:|--:|
| A: solo real | 0.8840 | 0.0014 | 0.9163 | 0.494 | 0.094 |
| B: real + 300 repetidos (control) | 0.8733 | 0.0024 | 0.9144 | 0.384 | 0.093 |
| C: real + 300 sintéticos | 0.8756 | 0.0015 | 0.9180 | 0.478 | 0.111 |

FPR en legítimos extra = proporción de hosts de valid_uy y test_hosting (todos legítimos) marcados como phishing con umbral 0.5.
