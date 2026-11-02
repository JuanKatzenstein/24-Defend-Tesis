# Generador de phishing sintético regional — criterio y modelo

Documentación de `tools/gen_sinteticos.py` (Fase 1) y su encaje con `plan_lote.py`
(Fase 2) y `validar_lote.py` (Fase 3). Cubre dos cosas que pide la defensa: el
**criterio de generación** (qué se genera, por qué y con qué reglas) y la
**explicación del modelo** (cómo y con qué límites interviene un modelo de lenguaje).

---

## 1. Criterio de generación (criterio escrito)

### 1.1 Objetivo y alcance

El detector necesita una **clase positiva regional etiquetada**. Los feeds reales
(OpenPhish, PhishTank) son globales y en inglés; el phishing rioplatense —marcas
locales (BROU, Itaú, Antel, SUCIVE, Mercado Pago…), palabras-gancho en español,
TLDs y plataformas concretas— aparece poco y sin etiquetar. El corpus sintético
cubre ese hueco **como caso de estudio**, no como train/test principal (eso sigue
siendo el resultado real OpenPhish + Tranco, ver `RESULTADOS.md`).

Qué se genera y qué **no**:

- **Sí:** *strings* de hostnames con forma de phishing, que son **etiquetas de
  entrenamiento** para que el clasificador aprenda a reconocerlos.
- **No:** registro de dominios, hosting, páginas, formularios de credenciales ni
  payloads. Elegir un nombre de dominio plausible no es la parte difícil ni escasa
  del phishing (cualquiera arma `marca+palabra+TLD`), así que el dataset no da
  ventaja operativa; sí le da a la tesis una clase positiva que no existe lista
  para bajar. El lado ofensivo/despliegue queda fuera de alcance a propósito.

### 1.2 Diseño en tres fases

| Fase | Script | Entrada → salida | Naturaleza |
|------|--------|------------------|-----------|
| 2 | `plan_lote.py` | proporciones del corpus → **plan** de parámetros | muestreo estadístico |
| 1 | `gen_sinteticos.py` | plan → **hostnames** (CSV esquema corpus) | realización |
| 3 | `validar_lote.py` | plan → reporte de QC | control analítico |

La Fase 2 decide *qué* generar (forma, gramática, TLD, marca, palabra, NN, estilo,
largo) por muestreo calibrado; la Fase 1 lo *realiza* en un host concreto; la Fase 3
audita que el plan respete la calibración y las reglas de no-repetición.

### 1.3 Gramáticas (de `plan_lote.py`, medidas en el corpus regional)

- **A1** — apex marca + palabra-gancho (`itau-beneficios.xyz`).
- **A2** — apex marca + sufijo corto sin sentido (`bbvaato.cf`).
- **A3a / A3b** — apex sin marca: nombre de negocio plausible / pseudo-palabra.
- **S1** — subdominio-ajeno: marca como subdominio sobre un dominio registrable ajeno.
- **S1b** — patrón `marca-gub.<etiqueta>.<tld>` (documentado solo para SUCIVE).
- **S2** — `www-<marca><NN>.<ajeno>` (prefijo `www-` + número).
- **S3** — dominio oficial incrustado completo (`brou.com.<ajeno>.com`).
- **P1–P4** — hosting de plataforma (pantheonsite.io / repl.co / vercel.app / otras).

### 1.4 Calibración

Pesos por forma (apex 0.44 / sub-ajeno 0.33 / plataforma 0.23) y repartos internos
tomados del informe de patrones del corpus. Son un primer ajuste revisable: la Fase 3
chequea que el lote muestreado no se aleje de esos objetivos más que la tolerancia.

### 1.5 Guardrails de validez (en la realización)

Cada host realizado se valida contra su fila del plan; si no pasa, se descarta y la
fila se realiza por la vía determinista (ver §2). Reglas:

- Etiquetas DNS válidas (solo `a-z0-9-`, sin guion al borde, ≤63; host ≤253).
- Termina en el TLD/plataforma de la fila.
- Contiene la **marca** si la fila la pide; refleja la palabra-gancho y el `NN`.
- No **copia** un ejemplo real ni reutiliza **tokens vedados** del lote.
- Largo dentro del objetivo (tolerancia blanda de ±6).
- Unicidad de host en todo el lote.

### 1.6 No-repetición y defecto conocido

La Fase 2 evita repetir la combinación `(marca, gramática)` entre filas. Para las
gramáticas que **fuerzan** la marca (`S1b`→sucive, `S3`→brou) o que **no** llevan
marca (`A3a`, `A3b`), el chequeo se hace sobre la marca sorteada pero `fila()` la
reescribe después, así que esas combinaciones sí se repiten. La Fase 3 lo reporta
como `(None, A3a)`, `(sucive, S1b)`, etc. **Es un defecto real del generador, está
documentado, y no se parchó** (la Fase 2 no se tocó): justamente es lo que un
validador debe cazar.

### 1.7 Salida y reproducibilidad

El CSV sale en el **mismo esquema que `data/raw/corpus_sintetico.csv`**
(`url,host,status,…,H1..H4,plat_cualquiera`), más dos columnas de trazabilidad
(`gramatica`, `fuente`). Las columnas de host (`subdominio/dominio_reg/sufijo/sld/
n_sub`) se derivan con **`tldextract`**, cuyo comportamiento por defecto reproduce
la convención del corpus (p. ej. `x.vercel.app` → registrable `vercel.app`, sufijo
`app`; `x.github.io` → `github.io` / `io`). Así el lote sirve tanto para entrenar
(`build_dataset.py` solo usa `url`) como de corpus de ejemplos para la propia Fase 2.
El `--seed` fija el **plan** y lo hace reproducible.

---

## 2. Explicación del modelo (modelo generador)

### 2.1 Rol del modelo

En la Fase 1 el modelo de lenguaje cumple un rol acotado: **redactar un hostname por
fila del plan**, imitando la *forma* de los ejemplos reales (nunca copiándolos) y
respetando los parámetros. El modelo no decide proporciones, marcas ni gramáticas:
eso lo fija la Fase 2. Es un "realizador" de un plan ya acotado.

### 2.2 Configuración

- **API key:** `TESIS_ANTHROPIC_API_KEY` (verificada: `sk-ant-…`, 106 chars). El
  script tolera también `HESIS_ANTHROPIC_API_KEY` y `ANTHROPIC_API_KEY`.
- **Modelo:** `claude-sonnet-5-5` por defecto (`--model` lo cambia).
- **SDK:** `anthropic` 2.3.0. Salida pedida como **array JSON estricto**
  (`{id, host, path}`), con parseo robusto (tolera fences). Batches de 25 filas.
- **`temperature`:** el gateway de esta sesión la rechaza (HTTP 400, *"Extra inputs
  are not permitted"*), así que **se omite**. La variabilidad entre hosts la aporta
  el muestreo del plan (Fase 2); la realización no es determinista por diseño.

### 2.3 Hallazgo: el modelo declina esta generación

Con el prompt descrito, los modelos actuales **declinan** la tarea: la respuesta
vuelve con `stop_reason = "refusal"` y sin contenido. Es una decisión de **política
de seguridad del modelo** ante la generación de hostnames que suplantan marcas
reales, aun en marco defensivo.

**Postura adoptada:** la negativa **no se reintenta ni se reescribe** el prompt para
esquivarla (nada de dividir la tarea, ocultar la intención o pedirle al modelo que
ignore su política). Eso sería eludir una medida de seguridad. La negativa se trata
como terminal y se registra.

### 2.4 Realización determinista (vía efectiva)

Como el plan igual debe realizarse, `gen_sinteticos.py` incluye un **realizador
determinista** por plantillas (una por gramática) que **no involucra al modelo** y
produce las mismas etiquetas de entrenamiento a partir del plan. La columna `fuente`
marca el origen de cada fila (`modelo` / `determinista`), de modo que el dataset es
auditable. La vía por modelo queda en el código, intacta, para entornos o modelos
donde esté habilitada; hoy el lote se realiza 100% por la vía determinista.

Esto es coherente con el criterio: escribir en código plantillas de strings
`marca+palabra+TLD` para armar datos de entrenamiento es tarea de programación
normal del lado defensivo; no tiene dimensión de seguridad del modelo ni da uplift.

### 2.5 Limitaciones (importantes para la defensa)

- **Sesgo del realizador determinista:** las pseudo-palabras se arman alternando
  vocal/consonante (`axatamodirot`, `iqevucohute`), un patrón **más regular** que el
  phishing real. Un clasificador podría aprender ese patrón de carácter como atajo
  en lugar de señal de phishing. Hay que vigilarlo con `ablation.py` (el mismo
  control de fugas del resto del trabajo) y **no usar el sintético como train/test
  principal** — queda como caso de estudio, igual que antes.
- **Determinismo:** con `--seed` fijo, el realizador determinista reproduce el lote
  exacto; la vía por modelo (si se habilitara) no sería reproducible.
- **Cobertura:** el lote imita las gramáticas medidas; patrones nuevos de phishing
  no representados en el corpus no aparecen.

---

## 3. Resultados del lote (n=125, seed 20251102)

- **125 hosts únicos**, todos DNS-válidos. Fuente: **125 deterministas / 0 del
  modelo** (el modelo declinó; ver §2.3).
- **Fase 3 (`validar_lote.py`):** distribución por forma dentro de tolerancia
  (apex 0.47 / sub 0.25 / plataforma 0.28 vs. 0.44/0.33/0.23); NN únicos; palabras
  balanceadas. "REVISAR" por los combos repetidos de §1.6 (defecto conocido).
- **Integración (`build_dataset.py` + `features.py`):** 216 filas
  (125 phishing / 91 legit), 32 features. Sin cambios en el pipeline de detección.

### Archivos

- `tools/gen_sinteticos.py` — generador (Fase 1).
- `data/raw/sinteticos_lote.csv` — lote de 125 hosts (esquema corpus + `fuente`).
- `data/processed/plan_lote_125.json` — plan crudo (Fase 2).
- `data/processed/dataset_sintetico_125.csv` — dataset etiquetado + features.
- `reports/validacion_lote_125.md` — reporte de la Fase 3 sobre el plan.
