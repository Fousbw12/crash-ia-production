#!/bin/bash
pkg install inotify-tools -y
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}==================================================${NC}"
echo -e "${BLUE}   SURVEILLANCE ET SAUVEGARDE AUTOMATIQUE GITHUB   ${NC}"
echo -e "${BLUE}==================================================${NC}"
echo -e "L'IA enregistre les fichiers... Git va synchroniser en continu."

while true; do
    # Écoute les modifications des fichiers du projet
    inotifywait -r -e modify -e create -e delete --exclude "(^\..*|\.git)" ./
    
    echo -e "${GREEN}\n[GIT AUTOMATIQUE] Changement détecté ! Envoi à GitHub...${NC}"
    
    # Exécution des commandes Git avec ton Token 100% automatisé
    git add .
    git commit -m "Auto Update Session IA : $(date +'%H:%M:%S')"
    git push https://github.com main
    
    echo -e "${GREEN}[SUCCÈS] Dépôt GitHub mis à jour et synchronisé.${NC}"
    echo "En attente de la prochaine modification..."
    echo "--------------------------------------------------"
    sleep 2
done
