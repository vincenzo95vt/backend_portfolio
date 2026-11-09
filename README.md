# 📁 Portfolio Backend (FastAPI)

Este es un backend minimalista hecho con **FastAPI** para gestionar mi portfolio personal desde una interfaz web privada. ESte proyecto ha sido creado para actualizar datos de forma sencilla. 

Además, expone un **servidor MCP remoto** en `/mcp` para que Claude (claude.ai como conector personalizado, Claude Code o cualquier cliente MCP) pueda leer y actualizar el contenido del portfolio.

---

## 🚀 Tecnologías

- FastAPI
- Jinja2
- Uvicorn / Gunicorn
- MongoDB (Motor)
- FastMCP (servidor MCP, transporte Streamable HTTP, OAuth con GitHub)
- Python 3.12+

---

## ▶️ Arrancar en local

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt   # incluye requirements.txt + herramientas de test

# crea un .env con las variables de la tabla de abajo
uvicorn app.main:app --reload --port 8000
```

- Web pública: http://localhost:8000
- Panel de administración: http://localhost:8000/login
- API JSON: http://localhost:8000/api/v1/projects (también `experience`, `education` y `about_me`)
- Servidor MCP: http://localhost:8000/mcp. Solo se monta si están definidas las variables OAuth (ver más abajo). Al arrancar, el log muestra `🤖 Servidor MCP disponible en /mcp` o un aviso con las variables que faltan.

En producción (Render):

```bash
gunicorn app.main:app -k uvicorn.workers.UvicornWorker -w 2
```

---

## 🔐 Variables de entorno

| Variable | Obligatoria | Descripción |
|---|---|---|
| `MONGOCLUSTER` | Sí | URI de conexión a MongoDB (Atlas). |
| `CLAVESECRETA` | Sí | Clave para firmar la cookie de sesión del panel. |
| `MONGO_DB_NAME` | No | Nombre de la base de datos. Por defecto, `Portfolio_backend`. Úsala para probar contra una BD separada (ver abajo). |
| `MCP_BASE_URL` | Para MCP | URL pública de la app **sin** `/mcp`: `http://localhost:8000` en local y `https://tu-dominio` en producción. Se usa para construir las URLs OAuth. |
| `GITHUB_CLIENT_ID` | Para MCP | Client ID de la GitHub OAuth App. |
| `GITHUB_CLIENT_SECRET` | Para MCP | Client secret de la GitHub OAuth App. |
| `MCP_ALLOWED_GITHUB_USERS` | Para MCP | Logins de GitHub autorizados, separados por comas (p. ej. `pablovasta`). Cualquier otro usuario recibe un 401 aunque complete el login. |
| `MCP_JWT_SIGNING_KEY` | Para MCP | Secreto aleatorio de 32 caracteres o más. Firma los tokens que emite el servidor y cifra el estado OAuth guardado en Mongo. Generar con `python -c "import secrets; print(secrets.token_urlsafe(48))"`. **Si la rotas, hay que reconectar el conector** (ver [rotación](#claves-y-qué-pasa-si-rotas-mcp_jwt_signing_key)). |
| `MCP_ENV` | No | `development` permite redirecciones OAuth a `http://localhost:*` y `http://127.0.0.1:*` (necesario para MCP Inspector). Con cualquier otro valor, o sin definir, **solo** se acepta el callback de claude.ai. **No la definas en producción.** |

Si falta cualquiera de las variables "Para MCP", o si `MCP_JWT_SIGNING_KEY` es demasiado corta, `/mcp` **no se monta**: nunca queda expuesto sin autenticación. El resto de la app funciona igual.

> ⚠️ **Rota `CLAVESECRETA`.** Hasta ahora, el arranque del servidor imprimía su valor en los logs (`🔑 Clave secreta: ...`). Esa línea ya se ha eliminado, pero el valor puede seguir en los logs de Render. Genera una nueva (`python -c "import secrets; print(secrets.token_urlsafe(48))"`) y actualízala en Render y en tu `.env`. Al cambiarla se cierran las sesiones abiertas del panel y hay que volver a iniciar sesión.

---

## 🤖 Servidor MCP

### Herramientas

| Entidad | Herramientas |
|---|---|
| Proyectos | `list_projects`, `get_project`, `create_project`, `update_project` |
| Experiencia | `list_experiences`, `get_experience`, `create_experience`, `update_experience` |
| Formación | `list_educations`, `get_education`, `create_education`, `update_education` |
| Sobre mí (skills, idiomas…) | `get_about_me`, `update_about_me` (documento único, sin list/create) |

- **No hay herramientas de borrado.** Para borrar se usa el panel.
- **Orden:** proyectos, experiencia y formación tienen un campo opcional `orden` (entero de 0 a 100000; el número más bajo aparece primero). Los elementos sin `orden` van al final, en orden de creación. Las herramientas `list_*`, la API `/api/v1/*` y el panel devuelven los datos ya ordenados. Se puede cambiar desde `create_*`/`update_*` o desde los formularios del panel; en el panel, dejar el campo vacío al editar quita el orden.
- Los `update_*` son parciales: solo cambian los campos enviados. Los campos de lista (`tecnologias`, `hardSkills`…) se sustituyen enteros.
- Las entradas se validan con Pydantic: textos no vacíos, URLs http(s), listas no vacías y sin campos desconocidos. Los errores indican qué campo ha fallado y por qué. Los ids que no existen o son inválidos devuelven un mensaje que indica qué `list_*` usar.
- Las herramientas reutilizan la misma capa de servicios que el panel ([app/services/portfolio.py](app/services/portfolio.py)), así que se guardan los mismos formatos que lee el frontend.

### Autenticación (OAuth con GitHub)

claude.ai solo admite conectores con OAuth, así que `/mcp` se protege con OAuth delegando el login en GitHub:

1. claude.ai (o Inspector) se registra dinámicamente en `/register` y redirige a `/authorize`.
2. Aparece una pantalla de consentimiento y después el login de GitHub (solo se pide el permiso `read:user`).
3. Si tu login está en `MCP_ALLOWED_GITHUB_USERS`, el servidor emite un token y el cliente ya puede usar `/mcp`.

El estado OAuth (clientes registrados, tokens) se guarda **cifrado** en Mongo, en colecciones con el prefijo `mcp_oauth`. Así sobrevive a los reinicios y se comparte entre workers. El servidor MCP funciona en modo *stateless*, por lo que cualquier worker de gunicorn puede atender cualquier petición.

### Claves y qué pasa si rotas `MCP_JWT_SIGNING_KEY`

`MCP_JWT_SIGNING_KEY` es la única clave del lado MCP y cumple dos funciones:

- **Firma los tokens** (de acceso y de refresco) que el servidor entrega a claude.ai.
- **Cifra el estado OAuth guardado en Mongo** (Fernet). La clave de cifrado no es el valor tal cual: se deriva de él con HKDF-SHA256 y la sal `portfolio-mcp-oauth-storage`.

**Reiniciar o redesplegar con la misma clave no afecta a nada:** el conector sigue funcionando.

**Si rotas la clave** (porque se ha filtrado, por ejemplo):

1. Todos los tokens emitidos dejan de ser válidos y `/mcp` responde `401`.
2. El estado guardado en Mongo ya no se puede descifrar. No da error: se trata como si no existiera, así que el registro de claude.ai y sus tokens desaparecen.
3. **Hay que reconectar el conector:** en claude.ai, *Settings → Connectors*, desconéctalo y vuelve a conectarlo (consentimiento + login de GitHub). Si da error, elimínalo y añádelo de nuevo con la misma URL. Lo mismo con MCP Inspector.
4. Los documentos viejos se quedan en las colecciones `mcp_oauth*` sin poder leerse. Puedes borrar esas colecciones sin problema: se recrean solas.
5. Opcional: en GitHub, *Settings → Applications → Authorized OAuth Apps*, puedes revocar la app para invalidar también los tokens de GitHub antiguos.

Los datos del portfolio no se tocan. Rotar `CLAVESECRETA` (sesión del panel) no afecta al conector, y rotar `MCP_JWT_SIGNING_KEY` no afecta al panel.

### Crear la GitHub OAuth App

En GitHub → *Settings → Developer settings → OAuth Apps → New OAuth App*. Crea **una para local y otra para producción**, porque cada una admite un solo callback:

| Campo | Local | Producción |
|---|---|---|
| Homepage URL | `http://localhost:8000` | `https://backend-portfolio-iqkc.onrender.com` |
| Authorization callback URL | `http://localhost:8000/auth/callback` | `https://backend-portfolio-iqkc.onrender.com/auth/callback` |

Copia el *Client ID* y genera un *Client secret* para `GITHUB_CLIENT_ID` y `GITHUB_CLIENT_SECRET`.

### Probar en local con MCP Inspector

1. Usa una **base de datos separada** para no tocar los datos reales. Añade a tu `.env`:

   ```env
   MONGO_DB_NAME=Portfolio_backend_dev
   MCP_ENV=development
   MCP_BASE_URL=http://localhost:8000
   GITHUB_CLIENT_ID=...          # de la OAuth App local
   GITHUB_CLIENT_SECRET=...
   MCP_ALLOWED_GITHUB_USERS=tu-login-de-github
   MCP_JWT_SIGNING_KEY=...       # secrets.token_urlsafe(48)
   ```

   Con `MONGO_DB_NAME` apuntando a otra BD, el panel local también trabaja contra ella. Puedes crear un usuario del panel con `python -m app.middlewares.create_user`.

2. Arranca la app: `uvicorn app.main:app --reload --port 8000`
3. En otra terminal: `npx @modelcontextprotocol/inspector`. Se abre en http://localhost:6274.
4. En Inspector, elige **Transport Type: Streamable HTTP** y **URL: `http://localhost:8000/mcp`**, y pulsa **Connect**. Inspector arranca el flujo OAuth: acepta el consentimiento, inicia sesión en GitHub y vuelve a Inspector. Si quieres ver cada paso, usa *Open Auth Settings → Guided OAuth Flow*.
5. En **Tools → List Tools** deberían aparecer las 14 herramientas. Prueba `list_projects` y, por ejemplo, `create_project` con:

   ```json
   {"project": {"nombre": "Prueba", "descripcion": "Desde Inspector", "tecnologias": ["Python"]}}
   ```

Comprobación rápida sin cliente: `curl -i -X POST http://localhost:8000/mcp` debe devolver `401` con una cabecera `WWW-Authenticate`.

### Conectar en claude.ai

*Settings → Connectors → Add custom connector*:

- **URL:** `https://backend-portfolio-iqkc.onrender.com/mcp`
- *Advanced settings* (Client ID/Secret): **déjalos vacíos**. claude.ai se registra solo mediante registro dinámico.

Al pulsar *Connect* se abre el consentimiento y el login de GitHub. Después, activa el conector en una conversación.

### Despliegue (Render)

- **HTTPS:** Render ya lo proporciona. `MCP_BASE_URL` tiene que ser exactamente la URL pública `https://…` (sin `/mcp` ni barra final). Si pones un dominio propio delante, usa ese dominio en `MCP_BASE_URL`, en la OAuth App de GitHub y en claude.ai.
- **Variables:** `MCP_BASE_URL`, `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`, `MCP_ALLOWED_GITHUB_USERS` y `MCP_JWT_SIGNING_KEY`. **No** definas `MCP_ENV` ni `MONGO_DB_NAME`.
- **CORS:** no hay que cambiar nada. claude.ai se conecta a `/mcp` desde sus servidores, no desde el navegador, y el CORS actual solo afecta al frontend.

---

## 🧪 Tests

```bash
pip install -r requirements-dev.txt
pytest
```

Usan una base de datos en memoria (`mongomock-motor`) y nunca se conectan a Mongo real:

- `tests/test_rest_regression.py`: fija el comportamiento del REST y del panel (URLs, redirecciones, formato JSON).
- `tests/test_mcp_tools.py`: las 14 herramientas, sus validaciones y mensajes de error, y comprueba que no exista ninguna herramienta de borrado.
- `tests/test_mcp_auth.py`: 401 sin token, metadatos OAuth, redirect URIs permitidas según `MCP_ENV`, lista blanca de usuarios, que `/mcp` no se monte sin configuración y que, al rotar `MCP_JWT_SIGNING_KEY`, los registros y tokens antiguos dejen de valer.
