# Validación de lote — lote_demo.json

Casos: 20 · tolerancia ±0.15

**Resultado global: ✅ PASA**

## 1. Distribución por forma (vs. objetivo)

| forma | objetivo | observado | n | desvío | estado |
|-------|---------:|----------:|--:|-------:|:------:|
| apex | 0.44 | 0.45 | 9 | +0.01 | OK |
| sub_ajeno | 0.33 | 0.30 | 6 | -0.03 | OK |
| plataforma | 0.23 | 0.25 | 5 | +0.02 | OK |

Tolerancia: ±0.15 sobre la proporción. (Con n=20 chico, un desvío aislado es ruido de muestreo esperable.)

## 2. Combinaciones (marca, gramática) repetidas

- OK: sin repeticiones dentro del lote.

## 3. Unicidad de NN

- OK: 4 NN, todos únicos.

## 4. Balance de palabras-gancho

- 11 palabras distintas; la más usada «ingreso» = 9% del total → OK

