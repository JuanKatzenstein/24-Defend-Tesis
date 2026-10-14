# Split aleatorio vs. grouped por dominio registrable

- Dataset: 4633 hosts · 3690 dominios registrables (grupos)
- Hosts por grupo: máx 72 (pages.dev), media 1.3
- Grupos con etiquetas mixtas (phishing + legit en el mismo dominio): 21

Familias grandes (fuente de fuga si se reparten entre train/test):
  - `pages.dev`: 72 hosts
  - `vercel.app`: 47 hosts
  - `000webhostapp.com`: 41 hosts
  - `pantheonsite.io`: 33 hosts
  - `repl.co`: 33 hosts
  - `linkedin.com`: 27 hosts

| Modelo | split | ROC-AUC | F1 |
|--------|-------|--------:|---:|
| LogReg | aleatorio | 0.925 | 0.798 |
| LogReg | **grouped** | **0.922** | **0.792** |
| LogReg | caída | -0.003 | -0.006 |
| RandomForest | aleatorio | 0.943 | 0.850 |
| RandomForest | **grouped** | **0.937** | **0.830** |
| RandomForest | caída | -0.006 | -0.020 |

**Lectura:** la caída al pasar a grouped es la fuga por familias que el split aleatorio ocultaba. Los números grouped son los que hay que reportar en la tesis.
