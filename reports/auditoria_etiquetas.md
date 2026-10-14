# Auditoría de etiquetas del corpus combinado

Revisión de calidad de las etiquetas antes de confiar en la base para entrenar.
Dos frentes: (1) búsqueda de errores de etiqueta en los positivos, (2) revisión
a mano del núcleo uruguayo.

## 1. ¿Hay phishing mal etiquetado?

Se auditaron los positivos que "parecen infraestructura" (hostnames de AWS/Azure,
IPs, buckets S3). **Conclusión: no son errores de etiqueta.** La enorme mayoría es
phishing real alojado en la nube, con la marca en el subdominio:

- `itaucard.s3.amazonaws.com`, `mercadopago.azurewebsites.net`,
  `itaucard-atualizacao-cadastral2.azurewebsites.net`, etc. → phishing legítimo.

Quedan **16 positivos sin ninguna señal léxica de marca ni palabra** — buckets S3
con nombre aleatorio, hostnames EC2, IPs inversas:

```
aajdowijiwsd.s3.eu-north-1.amazonaws.com   ec2-34-240-18-152.eu-west-1.compute.amazonaws.com
aajodiwsd.s3.eu-north-1.amazonaws.com      ec2-35-163-148-221.us-west-2.compute.amazonaws.com
aaoidjwid.s3.eu-north-1.amazonaws.com      ec2-52-208-200-37.eu-west-1.compute.amazonaws.com
ajoidjwoisd.s3.eu-north-1.amazonaws.com    ersfgifgwu.s3.ca-central-1.amazonaws.com
amajidjwi.s3.eu-north-1.amazonaws.com      ssskidwjw.s3.eu-north-1.amazonaws.com
ananolgikd.s3.sa-east-1.amazonaws.com      wiajijsd.s3.eu-north-1.amazonaws.com
133.185.205.92.host.secureserver.net       81.246.109.208.host.secureserver.net
3edorzj9tvjw5tgptn2y.s3.amazonaws.com      e47c1mbih9y6y9x80nvv.s3.amazonaws.com
```

**Decisión: se conservan** (son phishing real), y se marcan con `senal_lexica=False`
en `corpus_regiones.csv` para poder reportarlos aparte. No se eliminó ninguna fila.

### ¿Son el "piso ciego" del detector solo-URL?

Se midió el recall out-of-fold (RF, 5-fold, seed 42) separando por este tag:

| subconjunto | recall | n |
|-------------|-------:|--:|
| todos los positivos | 0.792 | 1440 |
| positivos "ciegos" (sin marca, infra) | **1.000** | 16 |
| positivos detectables (con señal) | 0.790 | 1424 |

Resultado contraintuitivo pero favorable: **el modelo igual atrapa los 16**, porque
los nombres aleatorios (`aajdowijiwsd`) tienen **alta entropía y host largo**, que
son features léxicas reales. Excluirlos cambia el recall global solo 0.792→0.790.
Es decir, **no hay un piso ciego problemático**: ni distorsionan las métricas ni
hay motivo para quitarlos.

## 2. Revisión a mano de los 42 casos uruguayos

| marca | n | veredicto |
|-------|--:|-----------|
| BROU | 10 | phishing UY inequívoco |
| Antel | 11 | phishing UY (incluye `antel*.click` cortos, temáticos de Antel) |
| SUCIVE | 8 | phishing UY inequívoco (patrón `-gub` clásico) |
| Prex | 9 | phishing UY inequívoco |
| OCA | 1 | phishing UY (`ocaverifyserviceweb.gt.tc`) |
| Redpagos/MiDinero | 1 | phishing UY (`redpagomidinerouy.wixsite.com`) |
| **dudoso** | 1 | `trick.com.uy` — dominio `.uy` real, pero "trick" no identifica marca; no verificable sin visitarlo |

**41 de 42 confirmados** como phishing uruguayo real. El único incierto,
`trick.com.uy`, se deja etiquetado pero anotado como caso a verificar.

## Conclusión

Las etiquetas del corpus son **de buena calidad**: no se encontró mal-etiquetado
sistemático. La "limpieza" se reduce a (a) un tag de transparencia para los 16
positivos de infraestructura y (b) una marca de duda sobre un único caso UY. **No
se eliminó ninguna fila**, así que las métricas de los reportes previos siguen
válidas.
