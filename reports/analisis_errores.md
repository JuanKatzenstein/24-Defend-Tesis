# Análisis de errores — detector baseline (Random Forest)

Evaluación con **validación cruzada** (5-fold estratificado, umbral 0.5) sobre el
dataset de 111 URLs (20 phishing / 91 legítimas, incluidos 31 *hard negatives*).

**Errores: 4 / 111.** Todos caen en los casos genuinamente difíciles — no son
ruido, son frontera de decisión real. Esto es lo que hay que discutir en la tesis.

## Falsos positivos (legítimas marcadas como phishing)

| prob. phishing | URL | por qué confunde |
|---:|---|---|
| 0.55 | `login.microsoftonline.com/...oauth2/authorize` | login legítimo real: palabra-gancho "login" + subdominio + path de autenticación. Es el desafío clásico: los portales de login legítimos comparten superficie con el phishing. |
| 0.63 | `nextjs-commerce.vercel.app` | deploy legítimo en plataforma de hosting gratuito (`vercel.app`), misma plataforma que usan campañas de phishing. |
| 0.65 | `linkedin.com` | dominio pelado, corto, sin `www`. Poca "masa léxica" para decidir. |

## Falsos negativos (phishing no detectado)

| prob. phishing | URL | por qué evade |
|---:|---|---|
| 0.44 | `ocazrv.xyz` | phishing *apex* minimalista: corto, TLD barato, **sin palabras-gancho** ni subdominios ni dígitos. Cuando el atacante no usa señuelos léxicos, el detector basado en cadena se queda sin señal. |

## Conclusiones para la tesis

1. **Los errores no son aleatorios: son estructurales.** El detector falla justo
   donde la señal léxica es ambigua (logins legítimos) o ausente (phishing apex
   minimalista). Esto acota qué puede y qué no puede un detector *solo-URL*.
2. **El hosting en plataformas gratuitas es un eje de confusión real**, no un
   artefacto: hay uso legítimo y malicioso de `vercel.app`, `github.io`, etc.
   Sugiere complementar con señales no-léxicas (edad del dominio, certificado,
   reputación) en trabajo futuro.
3. **Los falsos negativos apex sin señuelos** motivan features adicionales:
   similitud con marcas (distancia de edición a dominios objetivo), presencia en
   listas de registro reciente, etc.
