# Guide : utiliser 1min.ai comme LLM de vos agents

Ce guide explique comment installer la gateway et y brancher vos agents. Toutes les commandes
supposent que la gateway tourne sur `http://127.0.0.1:5001`.

## 1. Installer

```bash
cp .env.example .env
```

Dans `.env`, renseignez :

* `ONE_MIN_API_KEY` : votre clé 1min.ai. Elle reste sur le serveur, les agents ne la voient jamais.
* `GATEWAY_API_KEYS` : une entrée par agent, à générer avec :

```bash
docker compose run --rm gateway python -m gateway.cli create-key mon-agent
# ou, sans Docker : make key NAME=mon-agent
```

La commande affiche la clé de l'agent (`gw-...`, à garder) et l'entrée à copier dans
`GATEWAY_API_KEYS`, par exemple `mon-agent:3f1c...e9`. Plusieurs agents : séparez les entrées
par des virgules. Ajoutez `:120` à la fin d'une entrée pour lui donner 120 requêtes/minute.

```bash
docker compose up -d
curl http://127.0.0.1:5001/ready      # {"status": "ready", ...}
```

Pour révoquer un agent, retirez son entrée de `GATEWAY_API_KEYS` et relancez
(`docker compose up -d`).

> Exposition sur Internet : la gateway n'écoute que sur 127.0.0.1. Placez un reverse proxy
> HTTPS devant (Caddy : `reverse_proxy 127.0.0.1:5001`) pour que les clés ne circulent jamais
> en clair, et renseignez `MCP_ALLOWED_HOSTS` avec votre nom de domaine.

## 2. Choisir les modèles

`GET /v1/models` liste :

* les modèles **natifs** (API compatible OpenAI de 1min.ai) : vrais appels d'outils, streaming,
  mode JSON. À privilégier pour les agents ;
* les modèles **legacy** (Claude, Gemini, Grok, Perplexity…) : servis par l'API « Chat with AI ».
  Les outils y sont émulés par la gateway, ce qui marche bien avec de bons modèles mais reste moins
  fiable que le natif ;
* vos **alias** (`MODEL_ALIASES`).

Ces listes sont lues chez 1min.ai et mises à jour automatiquement (cache de 10 minutes). Le champ
`vision` indique si un modèle accepte des images. Les noms Claude courants
(`claude-haiku-4-5-20251001`, `claude-sonnet-4-6`) sont traduits vers les identifiants 1min.ai
(`us.anthropic.claude-...`). `GET /v1/features/{TYPE}/models` donne les modèles acceptés par une
feature (par exemple `/v1/features/YOUTUBE_SUMMARIZER/models`).

Les images, fichiers et la recherche web passent toujours par l'API legacy. Ajoutez `:online` au
nom d'un modèle (`gpt-4o-mini:online`) pour activer la recherche web.

Exemple utile si vos agents sont écrits pour Claude mais que vous voulez de vrais appels d'outils :

```
MODEL_ALIASES=claude-*=gpt-5.1
```

## 3. Brancher les agents

Réglez toujours les relances automatiques à 0 : 1min.ai facture chaque génération, et une requête
relancée est une nouvelle génération.

**SDK OpenAI (Python)**

```python
from openai import OpenAI

client = OpenAI(base_url="http://127.0.0.1:5001/v1", api_key="gw-...", max_retries=0)
reply = client.chat.completions.create(
    model="gpt-4o-mini", messages=[{"role": "user", "content": "Bonjour"}]
)
print(reply.choices[0].message.content)
```

**LangChain**

```python
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    base_url="http://127.0.0.1:5001/v1", api_key="gw-...", model="gpt-4o-mini", max_retries=0
)
```

**CrewAI**

```python
from crewai import LLM

llm = LLM(model="openai/gpt-4o-mini", base_url="http://127.0.0.1:5001/v1", api_key="gw-...")
```

**n8n, Open WebUI, LibreChat, Flowise…** : choisissez un fournisseur « OpenAI compatible », URL de
base `http://127.0.0.1:5001/v1`, clé `gw-...`.

**SDK Anthropic**

```python
import anthropic

client = anthropic.Anthropic(base_url="http://127.0.0.1:5001", api_key="gw-...", max_retries=0)
message = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1024,
    messages=[{"role": "user", "content": "Bonjour"}],
)
```

**Agents compatibles Anthropic par variables d'environnement**

```bash
export ANTHROPIC_BASE_URL=http://127.0.0.1:5001
export ANTHROPIC_API_KEY=gw-...
```

Pensez à un alias (`MODEL_ALIASES=claude-*=gpt-5.1`) pour que les noms de modèles Claude envoyés
par ces outils soient servis par un modèle natif avec de vrais appels d'outils. Les contextes très
longs dépassent la limite de l'API native de 1min.ai (100 000 caractères par requête).

## 4. Outils MCP

Ajoutez la gateway comme serveur MCP « Streamable HTTP » :

* URL : `http://127.0.0.1:5001/mcp`
* En-tête : `Authorization: Bearer gw-...`

Exemple de configuration (format courant des clients MCP) :

```json
{
  "mcpServers": {
    "1min": {
      "type": "http",
      "url": "http://127.0.0.1:5001/mcp",
      "headers": {"Authorization": "Bearer gw-..."}
    }
  }
}
```

Outils disponibles : `web_search`, `analyze_image`, `generate_image`, `text_to_speech`,
`transcribe_audio`, `upload_file`, `summarize_youtube`, `translate_text`, et `list_features` /
`run_feature` / `get_feature_result` pour toutes les autres features 1min.ai (vidéo, musique,
retouche d'image…).

## 5. Features 1min.ai en REST

```bash
# Catalogue
curl -H "Authorization: Bearer gw-..." http://127.0.0.1:5001/v1/features

# Traduction (attend le résultat)
curl -H "Authorization: Bearer gw-..." -H "Content-Type: application/json" \
  http://127.0.0.1:5001/v1/features/CONTENT_TRANSLATOR \
  -d '{"model": "gpt-4o", "prompt_object": {"prompt": "Hello", "originalLanguage": "en",
       "targetLanguage": "fr", "tone": "neutral", "domain": "General", "writingStyle": "Standard"}}'

# Vidéo (longue) : lancement asynchrone puis suivi
curl ... /v1/features/TEXT_TO_VIDEO -d '{"model": "kling", "mode": "async",
  "prompt_object": {"prompt": "un phare à l'aube", "duration": 5, "version": "1.6", "mode": "std"}}'
curl -H "Authorization: Bearer gw-..." http://127.0.0.1:5001/v1/features/results/<id>
```

Les champs de `prompt_object` sont ceux de la [documentation 1min.ai](https://docs.1min.ai/docs/api/intro).
Les fichiers (images, audio) s'envoient d'abord avec `POST /v1/files` ; l'`id` renvoyé s'utilise
comme `imageUrl` ou `audioUrl`.

## 6. Dépannage

| Symptôme | Cause probable |
|----------|----------------|
| 401 `invalid_api_key` | Clé `gw-...` absente de `GATEWAY_API_KEYS` (seule l'empreinte y figure) |
| 502 `upstream_authentication_failed` | `ONE_MIN_API_KEY` invalide ou révoquée |
| 404 `model_not_found` | Modèle inconnu : voir `/v1/models`, ou ajouter un alias / `LEGACY_CHAT_MODELS` |
| 429 `insufficient_quota` | Crédits 1min.ai épuisés ou `max_tokens` trop élevé |
| 400 sur `temperature` | Mettre `DROP_UNSUPPORTED_SAMPLING_PARAMS=true` |
| 504 `feature_still_processing` | Job long : utiliser `mode: "async"` et `/v1/features/results/{id}` |

Les logs (`docker compose logs -f gateway`) sont en JSON, sans contenu de conversation ; chaque
réponse porte un `X-Request-ID` à retrouver dans les logs.
