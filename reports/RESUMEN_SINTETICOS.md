# Phishing sintético generado con LLM — resumen de todo lo hecho

Datos: `data/raw/dataset_combinado_v4.csv` (train: 1114 phishing / 2711 legítimos; test: 283 / 637).
Generador: `tools/generar_sinteticos.py` (Claude por API, salida estructurada; los 10 lotes de cada
versión los rechazó `claude-opus-5-5` y los sirvió el modelo de respaldo `claude-opus-4-8`).
Evaluación: `tools/evaluar_sinteticos.py`; reportes completos en `reports/eval_sinteticos*.md`.

## Cuadro comparativo

| | Qué se le pidió al generador | Válidos / pedidos | KS mediano ↓ | Firma AUC n-gramas ↓ | Firma AUC features ↓ | RF: PR-AUC | RF: FPR legít. | N-gramas: PR-AUC | N-gramas: recall @ FPR 1% | N-gramas: FPR legít. |
|---|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| **Solo real (referencia)** | — | — | — | — | — | **0.8840** | 0.094 | **0.9165** | 0.728 | 0.027 |
| Control: repetir phishing real | — | — | — | — | — | 0.879–0.883 | 0.093–0.096 | 0.913–0.914 | 0.723–0.726 | 0.025–0.026 |
| v1 | Plan de forma, marca y sufijo + ejemplos reales | 245 / 250 | 0.10 | 0.98 | 0.98 | 0.8856 | 0.087 | 0.9163 | 0.746 | 0.027 |
| v2 | v1 + perfil real por fila (largo, guiones, dígitos, gancho) | 224 / 250 | 0.06 | 0.92 | 0.79 | 0.8865 | 0.096 | 0.9159 | 0.731 | 0.028 |
| v3 | Cada fila calcada de un host real ("molde") + palabras sobreusadas prohibidas | 208 / 250 | **0.05** | **0.63** | **0.50** | 0.8824 | 0.105 | 0.9166 | 0.728 | 0.033 |
| v4 | Moldes = los 217 phishing que el detector no detecta | 206 / 250 | 0.14 | 0.83 | 0.87 | 0.8801 | 0.104 | 0.9151 | 0.742 | 0.034 |
| v5 | Moldes = los 89 no detectados que imitan una marca | 147 / 250 | 0.13 | 0.89 | 0.91 | 0.8752 | 0.105 | 0.9173 | 0.731 | 0.026 |

Control de la generación dirigida (repetir los mismos moldes difíciles): RF 0.8652 (v4) y 0.8763 (v5);
n-gramas 0.9127 (v4) y 0.9169 (v5).

Cómo leer el cuadro:

- **KS mediano**: cuánto difieren, feature por feature, las distribuciones sintética y real (0 = iguales; objetivo ≤ 0.15).
- **Firma**: AUC de un clasificador entrenado para separar sintético de real. 0.5 = indistinguibles;
  cerca de 1 = el generador deja una "marca de fábrica". Objetivo ≤ 0.75.
- **RF**: detector Random Forest sobre 20 features léxicas del hostname (largo, guiones, dígitos, entropía,
  marca, typosquatting...). **N-gramas**: regresión logística sobre fragmentos de 1 a 4 caracteres del
  hostname (TF-IDF), es decir, un detector que "lee" el texto. Ambos se entrenan con train (+ los
  sintéticos) y se miden en el **test real**; media de 5 semillas.
- **PR-AUC**: calidad global del detector sobre phishing (1 = perfecto). **Recall @ FPR 1%**: qué fracción
  del phishing detecta cuando solo se tolera un 1% de falsas alarmas. **FPR legít.**: proporción de 949
  sitios legítimos extra (uruguayos y de hosting) marcados como phishing.
- El desvío entre semillas es de 0.001–0.003 en RF y casi 0 en n-gramas: las diferencias del orden de
  0.002 o menos son ruido.

## Explicación

Para ampliar la clase phishing se construyó un generador que le pide a un modelo de lenguaje (Claude, vía
API) hostnames de phishing nuevos, siguiendo un plan muestreado del propio corpus de entrenamiento. El
plan fija, por cada host, la forma (dominio propio, subdominio sobre un dominio ajeno o subdominio de una
plataforma de hosting gratuito), la marca imitada y el sufijo. Cada respuesta se valida automáticamente:
se descartan los hosts mal formados, los duplicados, las casi-copias de hosts reales y los que no respetan
el plan. Cada versión se evaluó con cinco chequeos: integridad (que no se filtren hosts del test),
fidelidad (que las distribuciones de las features coincidan con las reales, estadístico KS), diversidad,
firma (si un clasificador logra distinguir sintético de real) y utilidad (si un detector entrenado con
real + sintético mejora en el test real frente a uno entrenado solo con real y frente a un control que
simplemente repite phishing real). La primera versión mostró un problema típico de los LLM: los hosts
salían "de manual", con el doble de guiones y diez veces más palabras como *verificar* o *acceso* que el
phishing real, y un clasificador los separaba con AUC 0.98. Ese sesgo es peligroso porque el detector
puede aprender un atajo, "guiones + palabra gancho = phishing", que no se cumple en el phishing real y que
sí aparece en sitios legítimos (por ejemplo, *envios-rapidos.com.uy*). Primero se le pasó al modelo, para
cada host, el perfil de largo, guiones y dígitos de uno real (v2). Después se calcó cada host sobre un
"molde" real y se le prohibieron las palabras que venía repitiendo (v3). Con eso los sintéticos se
volvieron estadísticamente indistinguibles: firma AUC 0.50 sobre features, es decir, azar. Sin embargo,
justamente por ser iguales a los reales, no le enseñaron nada nuevo al detector: rindieron lo mismo que
repetir datos reales. Por eso se pasó a una generación dirigida, en la que los moldes fueron los phishing
de train que el detector no detecta, encontrados con validación cruzada para no tocar el test (v4 y v5).
Generar variaciones de esos casos fue mejor que repetirlos (0.880 contra 0.865 de PR-AUC), pero tampoco
superó al detector entrenado solo con real. Muchos de esos casos, como *skylark.ch* o *hilbarsteel.com*,
son por su nombre idénticos a un sitio legítimo; acercar el detector hacia ellos sube las falsas alarmas
(de 9.4% a ~10.5% en el Random Forest) y no deja ganancia neta. El mismo patrón se repitió con un segundo
detector basado en n-gramas de caracteres, que lee el texto completo del host. Ese detector rindió mejor
en general (PR-AUC 0.917 contra 0.884), pero con los sintéticos se mantuvo en su nivel: como mucho
ganó un par de puntos de recall (0.746 contra 0.728 con la v1) a costa de más falsas alarmas en v3 y v4.
La conclusión es que un LLM bien calibrado puede producir phishing sintético indistinguible del real,
pero en detección basada solo en el hostname eso no mejora al detector. El límite no está en la cantidad
de ejemplos, sino en la información que contiene el nombre: los errores que quedan son hosts de phishing
cuyo nombre no se diferencia del de un sitio legítimo, y ningún dato sintético de la clase phishing puede
resolver esa ambigüedad sin aumentar los falsos positivos.

## Problemas que generan los sintéticos (resumen)

1. **Firma del generador**: sin calibración, el LLM produce un estilo propio, reconocible (AUC 0.98).
2. **Atajos (shortcut learning)**: el detector puede aprender rasgos del generador en vez de rasgos del
   phishing, lo que sube los falsos positivos en sitios legítimos con esos rasgos.
3. **Redundancia**: si el sintético es indistinguible del real, equivale a sobremuestrear y no aporta información.
4. **Desplazamiento de la frontera**: generar alrededor de los casos difíciles empuja al detector hacia la
   zona de los legítimos (FPR de 9.4% a ~10.5% en el Random Forest).
5. **Trazabilidad**: el modelo pedido rechazó los lotes y los sirvió el modelo de respaldo; se registra en
   cada fila (`modelo_servido`) y hay que declararlo en la metodología.
6. **Fuga de información**: los moldes y la calibración salen solo de train; se verifica que ningún
   sintético esté a distancia de edición ≤ 1 de un host de valid/test.
