# 🚀 Guide de Déploiement

## Backend (API)

### Render (Recommandé)
1. Créer un compte sur https://render.com
2. Connecter votre repo GitHub
3. Créer un "Web Service"
4. Build Command : `pip install -r requirements.txt`
5. Start Command : `uvicorn api:app --host 0.0.0.0 --port $PORT`

### Railway
1. Créer un compte sur https://railway.app
2. Connecter votre repo
3. Déployer automatiquement

## Frontend (Dashboard)

### GitHub Pages
1. Push le code sur GitHub
2. Settings → Pages
3. Source : `main` branch, folder : `/dashboard`

### Netlify
1. Créer un compte sur https://netlify.com
2. Drag & drop le dossier `dashboard`
3. Ou connecter votre repo GitHub
