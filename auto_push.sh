#!/bin/bash
pkg install inotify-tools -y
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'
echo -e "${BLUE}==================================================${NC}"
echo -e "${BLUE}   SURVEILLANCE ET SAUVEGARDE AUTOMATIQUE GITHUB   ${NC}"
echo -e "${BLUE}==================================================${NC}"
while true; do
    inotifywait -r -e modify -e create -e delete --exclude "(^\..*|\.git)" ./
    echo -e "${GREEN}\n[GIT AUTOMATIQUE] Changement détecté ! Envoi à GitHub...${NC}"
    git add .
    git commit -m "Auto Update Session IA : $(date +'%H:%M:%S')"
    git push origin main
    sleep 2
done
