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

## Detalle técnico de lo que se hizo

Todo el trabajo con sintéticos está en cuatro scripts de Python dentro de `tools/`. Las cinco versiones
(v1 a v5) **no son cinco programas distintos**: son el mismo generador, `generar_sinteticos.py`, que se
fue modificando entre corridas. Cada versión quedó guardada como un commit del repositorio, junto con
su CSV de salida y su reporte, así que cualquiera puede reproducirla.

| Script | Para qué sirve |
|---|---|
| `generar_sinteticos.py` | Arma el pedido, llama a la API de Claude, valida la respuesta y guarda los hosts sintéticos en un CSV. |
| `evaluar_sinteticos.py` | Aplica los cinco controles de calidad (integridad, fidelidad, diversidad, firma y utilidad) y escribe el reporte. |
| `moldes_dificiles.py` | Encuentra los phishing de entrenamiento que el detector no detecta (los usan v4 y v5). |
| `test_generar_sinteticos.py` | Prueba de punta a punta del generador sin gastar API: simula el servidor de Claude en la propia máquina. |

### Cómo funciona el generador, paso a paso

Cada corrida pide *N* lotes de 25 hostnames. Cada lote recorre los mismos cinco pasos:

1. **Carga y calibración** (`cargar`, `forma_de`, `calibracion`). Se lee el CSV combinado y se toman
   **solo los phishing del split de entrenamiento**, para que el generador nunca vea ejemplos del test.
   `forma_de` clasifica cada host en una de tres formas: *apex* (dominio propio sin subdominios, como
   `itaucardigital.com`), *sub_ajeno* (subdominio sobre un dominio ajeno a la marca, como
   `americanas.divulgapromo.ml`) o *plataforma* (subdominio de un hosting gratuito, como
   `netflix-cop.vercel.app`). `calibracion` calcula las proporciones reales del corpus: qué porcentaje
   hay de cada forma, de cada sufijo (`.com`, `.com.br`...), de cada plataforma y de cada marca, y los
   percentiles de largo del hostname.
2. **Plan del lote** (`plan_lote`). Antes de llamar al modelo, el script decide qué tiene que tener
   cada uno de los 25 hosts (forma, marca, sufijo o plataforma), muestreando al azar con las
   proporciones del corpus. El modelo no decide la distribución: la decide el plan. Así el lote
   sintético respeta las mismas proporciones que el phishing real.
3. **Armado del prompt** (`SYSTEM`, `prompt_usuario`, `ejemplos`). El pedido tiene dos partes:
   - El **mensaje de sistema** fija el contexto (investigación defensiva, los hosts solo se usan para
     entrenar un clasificador y nunca se registran), las reglas de formato y la definición de las formas.
   - El **mensaje de usuario** incluye unos 18 ejemplos reales (6 por forma, rotados en cada lote), los
     percentiles de largo, los últimos 60 hosts ya generados (para que no se repita entre lotes) y el
     plan como una tabla, una fila por host.
4. **Llamada a la API** (`llamar`). Se usa el SDK oficial `anthropic` con **salida estructurada**: el
   modelo tiene que devolver un JSON que cumpla un esquema definido con Pydantic (`HostSintetico`,
   `Lote`), con los campos id, hostname, forma, marca y patrón. Eso evita tener que interpretar texto
   libre. Además:
   - el mensaje de sistema se guarda en caché, porque es igual en todos los lotes, y así se abaratan las
     llamadas;
   - no se usa *temperature*, porque el modelo pedido no la admite: la variedad sale del plan, de los
     ejemplos rotados y de la lista de hosts ya generados;
   - está activado el **fallback del servidor**: si el filtro de seguridad del modelo pedido
     (`claude-opus-5-5`) rechaza el pedido, la API lo reintenta con un modelo de respaldo
     (`claude-opus-4-8`). Fue lo que pasó en todos los lotes, y queda registrado en cada fila
     (`modelo_servido`).
5. **Validación** (`validar`, `motivo_rechazo`). Cada host devuelto se revisa contra su fila del plan y
   se descarta si:
   - no es un hostname válido (expresión regular `RE_HOST`);
   - ya existe en el dataset o ya fue generado (*duplicado*);
   - es una casi-copia: `esqueleto` quita dígitos y guiones, así `americanas-loja34` y
     `americanas-loja35` cuentan como el mismo host;
   - su largo cae fuera del rango real (percentiles 1 a 99);
   - no respeta el plan: `forma_host` y `dominio_registrado` recalculan la forma y el sufijo del host
     generado con la misma regla que se usó para el corpus, y tienen que coincidir con los de la fila.

Los hosts aceptados se guardan con sus metadatos (`fuente = sintetico_llm`, `split = train`, número de
lote, modelo pedido y servido, *effort*). Cada corrida escribe además un JSON de trazabilidad con la
configuración exacta (incluido un hash del prompt de sistema), cuántos hosts se pidieron, cuántos se
aceptaron y los motivos de descarte. Si el CSV de salida ya existe, el script continúa desde el último
lote sin repetir planes.

### Qué cambió en cada versión

**v1, plan por marginales.** Es el generador tal como se describió arriba. Cada atributo del plan se
sortea por separado con `muestrear` (forma, marca y sufijo, cada uno según su frecuencia en el corpus).
Problema: el plan solo controla forma, marca y sufijo; todo lo demás (largo, guiones, vocabulario) lo
decide el modelo, y el modelo tiende a un phishing "de manual", largo y descriptivo, como
`soporte-verificar-cuenta-itau.com`.

**v2, perfil real por fila.** `calibracion` guarda además, para cada forma, la lista de **perfiles
reales**: el largo, la cantidad de guiones, la cantidad de dígitos y si lleva palabra gancho de cada
host de entrenamiento. `plan_lote` copia un perfil al azar a cada fila, y la tabla del prompt suma las
columnas *largo, guiones, dígitos, gancho*. También se reescribió una regla del mensaje de sistema que,
sin querer, empujaba al modelo a usar palabras gancho. Resultado: el largo y los guiones quedaron como
los reales, pero el **vocabulario** seguía delatando al generador.

**v3, molde real por fila.** Es el cambio más importante. Se agregaron tres funciones:
- `moldes`: convierte cada phishing real de entrenamiento en un "molde" (1094 de 1114 sirven; se
  descartan los que la validación no clasificaría igual que el CSV). De cada molde salen **todos** los
  atributos de la fila: forma, marca, sufijo o plataforma, perfil y, en *sub_ajeno*, el mismo dominio
  base. Con esto el plan reproduce la distribución **conjunta** del corpus, no solo cada atributo por
  separado. Por ejemplo, si en el corpus Magalu aparece sobre todo en *apex* con `.com`, así aparece en el plan.
- `plan_lote`: ahora elige 25 moldes distintos al azar (`rng.sample`) y el prompt muestra el molde en la
  tabla. Se le pide al modelo un host "hermano" del molde: misma construcción (concatenado, gibberish,
  typosquatting, DNS dinámico...) pero con otro nombre.
- `tokens` y `sobreusadas`: parten cada host en palabras y comparan la frecuencia de cada palabra en lo
  ya generado con su frecuencia en el phishing real. Las palabras que el generador usa al menos 3 veces
  más que el corpus (por ejemplo *acesso*, *reembolso*, *cliente*) se listan en el prompt como
  palabras a evitar. Esa lista se recalcula en cada lote.

La validación suma dos reglas: en *sub_ajeno* el dominio registrado tiene que ser exactamente el del
molde, y el host no puede ser el molde con otros dígitos o guiones (*copia_del_molde*).

**v4, generación dirigida a los errores.** Se agregó el script `moldes_dificiles.py`, que hace una
**validación cruzada de 5 folds** sobre el entrenamiento, usando los folds que ya trae el CSV. En cada
fold entrena el detector (Random Forest de 300 árboles sobre las 20 features léxicas) con los otros
cuatro y predice el fold que dejó afuera. Así cada host recibe una probabilidad de phishing de un modelo
que nunca lo vio (predicción *out-of-fold*). Los phishing con probabilidad menor a 0.5 son los
**falsos negativos**: 217 de 1114. El generador recibe esa lista con la opción `--moldes` y solo usa esos
hosts como moldes. Como el pool es chico, `plan_lote` permite repetir un molde entre lotes.

**v5, dirigida y con marca.** Igual que v4, pero `moldes_dificiles.py --solo-con-marca` se queda solo con
los 89 falsos negativos que imitan una marca, que son los que tienen alguna señal léxica que aprender
(por ejemplo `magalulu.com`), y descarta los que no tienen ninguna pista en el nombre (por ejemplo
`skylark.ch`).

### Cómo funciona el evaluador

`evaluar_sinteticos.py` recalcula las features de **todos** los hosts (reales y sintéticos) con la misma
función, `extract_features` de `src/features.py`, para que ambos grupos pasen por el mismo pipeline.

| Control | Función | Cómo se mide |
|---|---|---|
| Integridad | `integridad` | Cuenta hosts inválidos, duplicados, ya presentes en el dataset y casi-copias. Para detectar **fuga hacia el test** busca, para cada sintético, el host de valid/test más parecido (vecino más cercano con similitud coseno sobre n-gramas de 2 a 4 caracteres) y cuenta cuántos están a distancia de edición (Levenshtein) de 1 o menos. |
| Fidelidad | `fidelidad` | Para cada una de las 20 features compara la distribución sintética con la real mediante el estadístico **Kolmogorov-Smirnov** (KS: la mayor distancia entre las dos curvas acumuladas; 0 = idénticas). Se reporta la mediana de los 20 valores. |
| Diversidad | `diversidad` | Similitud coseno de n-gramas de cada sintético con su vecino más cercano, dentro del lote y contra el phishing real. Arriba de 0.9 cuenta como casi-duplicado interno o como "memorización" de un host real. |
| Firma | `firma` | Arma un dataset balanceado, mitad sintéticos y mitad phishing real, y entrena dos clasificadores para distinguirlos: regresión logística sobre n-gramas de 1 a 4 caracteres y Random Forest sobre las 20 features. El AUC se mide con validación cruzada de 5 folds. También lista los n-gramas que más delatan al sintético. |
| Utilidad | `utilidad`, `utilidad_ngramas` | Entrena el detector cuatro veces, con 5 semillas cada una, y lo mide en el **test real**: A solo real; B real + phishing real repetido (sobremuestreo) en la misma cantidad que los sintéticos; C real + sintéticos; D real + moldes difíciles repetidos (solo en v4 y v5). Se hace con dos detectores: Random Forest sobre features (300 árboles, clases balanceadas) y regresión logística sobre TF-IDF de n-gramas de 1 a 4 caracteres. |

Los controles B y D son clave para la interpretación: sin ellos no se podría saber si una mejora viene
de la información nueva que aportan los sintéticos o simplemente de tener más ejemplos de la clase
phishing. `veredicto` resume todo en la tabla OK / REVISAR / FALLA con umbrales fijos: KS mediano ≤ 0.15,
firma ≤ 0.75 (FALLA si > 0.9), y ≤ 5% de casi-duplicados y de memorización.

### Cómo se probó el generador sin gastar API

`test_generar_sinteticos.py` levanta un servidor HTTP local que imita la API de Claude. El servidor lee
el plan desde el prompt, devuelve un host por fila y mete errores a propósito: una forma cambiada, un
hostname inválido y una copia de un lote anterior. Después corre el generador real contra ese servidor
y verifica 14 puntos:
- que el pedido use el modelo, el *effort*, la salida estructurada, el caché y el fallback correctos;
- que la validación descarte exactamente los errores introducidos;
- que al reanudar no se repitan planes;
- que el lote siguiente vea los hosts ya generados;
- que se escriba el reporte de trazabilidad.

El test se corrió después de cada cambio del generador.

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
