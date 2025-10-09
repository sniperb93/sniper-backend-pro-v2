# Emergent Flask Service (Docker)

## Prérequis
- Docker + Docker Compose
- Fichier `.env` à la racine de ce dossier (optionnel)
  - Exemples utiles:
    - FLASK_ENV=production
    - N8N_WEBHOOK_AUTH=enabled
    - N8N_WEBHOOK_TOKEN=your_secret_token

## Démarrage (dev)
```bash
cd emergent
docker compose up --build -d
```

L’application écoute sur http://localhost:5000

## Déploiement (prod)
- Option 1: utiliser directement `docker-compose.yml` (sans volume `.:/app` en prod pour figer l’image)
- Option 2: script shell
```bash
./deploy.sh
```

## Endpoints de base
- GET `/` → { status: "ok", service: "emergent" }
- Blueprints facultatifs:
  - `/builder` (si présents dans le code)
  - `/stripe`
  - `/trader`

Note: Ce service Flask est indépendant du backend FastAPI principal qui tourne via supervisor (0.0.0.0:8001, préfixe /api).