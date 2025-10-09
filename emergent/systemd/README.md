# Systemd Unit: emergent.service

Instructions d'installation (sur votre VPS Hostinger avec systemd):

1. Copier le fichier service
```bash
sudo mkdir -p /etc/systemd/system/
sudo cp emergent/systemd/emergent.service /etc/systemd/system/emergent.service
```

2. Mettre à jour les chemins dans le fichier (si besoin)
- WorkingDirectory=/chemin/vers/emergent → remplacez par le chemin réel, ex: /root/blaxing/emergent
- EnvironmentFile=/chemin/vers/emergent/.env
- ExecStart=/chemin/vers/emergent/venv/bin/gunicorn -w 4 -b 0.0.0.0:5000 main:app

3. Créer et activer l'environnement Python
```bash
cd /chemin/vers/emergent
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

4. Recharger systemd et démarrer le service
```bash
sudo systemctl daemon-reload
sudo systemctl enable emergent
sudo systemctl start emergent
sudo systemctl status emergent
```

5. Logs
- Journalctl: `sudo journalctl -u emergent -f`
- Le service redémarre automatiquement en cas d'échec (Restart=always)

Note: Ce service Flask est indépendant de l'app FastAPI principale de l'environnement Emergent. Utilisez ce service lorsque vous déployez la partie Flask (Emergent) sur votre hôte.