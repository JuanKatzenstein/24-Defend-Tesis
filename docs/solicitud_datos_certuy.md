# Solicitud de datos para investigación académica — CERTuy / AGESIC

> **Cómo usar esta plantilla.** Completá los campos entre `[corchetes]` con tus
> datos reales (nombre, universidad, tutor/a, carrera). Enviala por correo a
> CERTuy (incidentes@cert.uy / contacto institucional de AGESIC) y, si tu
> facultad lo permite, pedí que tu tutor/a figure en copia: un pedido avalado por
> la institución tiene mucho más peso. Ajustá el tono si tu universidad tiene un
> formato propio de nota formal.

---

**Asunto:** Solicitud de datos de incidentes de phishing para tesis de grado — uso académico

**Destinatario:** Centro Nacional de Respuesta a Incidentes de Seguridad Informática (CERTuy) — AGESIC

**Fecha:** [fecha]

Estimado equipo de CERTuy:

Me dirijo a ustedes en calidad de estudiante de [carrera] en [universidad], en el
marco de mi tesis de grado titulada (provisionalmente) *«Detección de phishing en
URLs y dominios mediante análisis léxico»*, bajo la tutoría de [nombre del/la
tutor/a] ([correo del/la tutor/a]).

El objetivo de mi trabajo es **defensivo**: construir y evaluar un detector que
clasifique dominios/URLs como phishing o legítimos *antes* de que la víctima
visite el sitio, a partir únicamente de la cadena del host (sin visitar ni
replicar los sitios maliciosos). Un hallazgo central de mi investigación es que
**el phishing dirigido a Uruguay está prácticamente ausente de los feeds públicos
internacionales** (verifiqué OpenPhish, URLhaus, PhishStats y los registros de
Certificate Transparency, con resultados casi nulos para marcas y dominios
uruguayos). Esto limita seriamente la posibilidad de evaluar un detector sobre
casos regionales reales.

Por este motivo, solicito respetuosamente si CERTuy podría compartir, con fines
exclusivamente académicos, un **conjunto de datos histórico de incidentes de
phishing que hayan afectado a entidades o marcas uruguayas**. Para minimizar
cualquier sensibilidad, el pedido se limita a la información estrictamente
necesaria:

- **URL o dominio/host** reportado como phishing;
- **fecha** de detección o reporte (idealmente, para permitir una evaluación con
  separación temporal);
- *opcionalmente*, la **marca o sector suplantado** (p. ej. banca, telco,
  gobierno).

**No requiero** datos personales de víctimas, contenido de los sitios,
direcciones IP de origen, ni ninguna información de identificación: únicamente el
listado de hosts maliciosos y su fecha.

Me comprometo a:

1. Usar los datos **solo para esta investigación académica**, sin fines
   comerciales.
2. **No republicar** los listados crudos; en la tesis se reportarían únicamente
   métricas agregadas y, a lo sumo, ejemplos ilustrativos anonimizados.
3. Resguardar los datos de forma segura y **eliminarlos** al finalizar el trabajo.
4. Cumplir con la normativa aplicable, incluida la Ley N.º 18.331 de Protección
   de Datos Personales.
5. **Citar a CERTuy** como fuente y compartir con ustedes los resultados y el
   detector resultante, por si fueran de utilidad para su labor.

Quedo a entera disposición para firmar cualquier acuerdo de confidencialidad o
convenio de uso de datos que consideren necesario, y para ajustar el alcance del
pedido a lo que les resulte viable. Agradezco desde ya su tiempo y el trabajo que
realizan.

Cordialmente,

[Nombre completo]
[Carrera] — [Universidad]
[Correo] · [Teléfono]
Tutor/a: [nombre] · [correo]

---

## Notas para vos (no enviar)

- **A quién más pedirle lo mismo**, en paralelo: CSIRTs/áreas de seguridad de
  BROU, Antel, Prex, Santander Uruguay, OCA. El encuadre es el mismo; cambia el
  destinatario y el párrafo de marcas.
- **APWG eCrime Exchange** (apwg.org): tiene membresía de investigación que suele
  ser gratuita para estudiantes y da acceso a una base histórica grande con mejor
  cobertura regional que los feeds libres. Vale la pena aplicar en paralelo.
- **Si CERTuy no puede compartir datos**, igual pueden orientarte sobre quién sí
  (bancos, proveedores de takedown) — pedir esa derivación también sirve.
- **Encuadre para la defensa:** que la data regional sea tan difícil de obtener no
  es una debilidad de tu tesis, es un **resultado**. Documentá este proceso de
  búsqueda (fuentes consultadas, resultados nulos, pedidos institucionales) como
  evidencia de la escasez estructural del phishing uruguayo en fuentes abiertas.
