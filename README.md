# 🚗 GateVision

**L'œil intelligent pour votre portail : reconnaissance de plaques locale, universelle et sans abonnement.**

GateVision est un addon open-source léger permettant d'automatiser l'ouverture de portails ou de portes de garage grâce à la lecture de plaques d'immatriculation. Contrairement aux solutions propriétaires, GateVision traite tout en local pour une confidentialité totale et une utilisation illimitée.

---

## ✨ Points forts

- 💸 **100% Gratuit & Illimité** : Pas de frais par scan ou d'abonnement mensuel.
- 🏠 **Confidentialité Totale** : Le flux vidéo ne quitte jamais votre réseau local.
- 🔌 **Universel** : Compatible avec n'importe quelle caméra IP (RTSP) et n'importe quel actionneur (Tuya, Shelly, MQTT, Webhooks).
- 🧠 **IA Intégrée** : Utilise EasyOCR pour une précision de lecture élevée même par faible luminosité.

---

## 🛠️ Comment ça marche ?

1. **Capture** : GateVision se connecte à votre caméra via le protocole RTSP.
2. **Analyse** : L'IA détecte et lit le texte sur les plaques d'immatriculation en temps réel.
3. **Validation** : Le système compare la plaque lue avec votre liste blanche (Whitelist).
4. **Action** : Si la plaque est autorisée, une commande est envoyée via MQTT ou Webhook pour ouvrir votre portail.

---

## 🚀 Installation rapide

### Pré-requis
- [Docker](https://www.docker.com/) installé sur votre machine (PC, NAS, ou Raspberry Pi).
- Une caméra IP supportant le flux RTSP.

### Installation
1. Clonez le dépôt :
   ```bash
   git clone [https://github.com/VOTRE_NOM/GateVision.git](https://github.com/VOTRE_NOM/GateVision.git)
   cd GateVision
