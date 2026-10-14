# Evaluación por región — ¿generaliza a los casos uruguayos?

Recall out-of-fold (5-fold, seed 42): cada host se predice con un modelo que no lo vio en entrenamiento.

| región | phishing | detectados | recall |
|--------|---------:|-----------:|-------:|
| UY | 42 | 40 | 0.952 |
| BR | 398 | 347 | 0.872 |
| otro | 1000 | 754 | 0.754 |

**Global:** recall phishing 0.792 · tasa de falsos positivos (legítimos marcados phishing) 0.059

## Casos UY no detectados
Apex minimalistas sin señal léxica (necesitan señales externas: edad del dominio, certificado, reputación DNS):
- `antel.gu.cc`
- `trick.com.uy`
