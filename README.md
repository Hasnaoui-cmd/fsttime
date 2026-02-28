# 📚 FSTTIME - Système Intelligent de Gestion des Emplois du Temps Universitaires

![Django](https://img.shields.io/badge/Django-5.x-green.svg)
![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)
![Status](https://img.shields.io/badge/Status-Production%20Ready-brightgreen.svg)

## 📋 Description du Projet

**FSTTIME** est une application web complète développée avec Django pour la gestion intelligente des emplois du temps universitaires. Ce système permet la planification automatisée des cours, la gestion des réservations de salles, et offre une interface moderne avec des notifications en temps réel.

### 🎯 Objectifs Principaux

- **Génération automatique** des emplois du temps avec détection de conflits
- **Gestion des réservations** de salles par les enseignants et associations
- **Système de notifications** en temps réel via WebSocket
- **Interface multilingue** entièrement en français
- **Contrôle d'accès basé sur les rôles** pour 5 types d'utilisateurs
- **Design moderne** avec style glassmorphism et animations fluides

---

## 🏗️ Architecture du Projet

### Structure des Applications

```
FSTTIME/
├── apps/
│   ├── accounts/       # Gestion des utilisateurs et authentification
│   ├── core/           # Modèles de base (salles, filières, groupes)
│   ├── scheduling/     # Emplois du temps et réservations
│   ├── notifications/  # Système de notifications temps réel
│   └── public/         # Pages publiques (accueil, contact)
├── config/             # Configuration Django
├── templates/          # Templates HTML
├── static/             # Fichiers statiques (CSS, JS, images)
├── scripts/            # Scripts d'utilité et maintenance (Nouveau)
└── manage.py
```

### Technologies Utilisées

| Composant | Technologie |
|-----------|-------------|
| **Backend** | Django 5.x, Python 3.11+ |
| **Base de données** | MySQL (production) / SQLite (développement) |
| **Frontend** | HTML5, CSS3, JavaScript, TailwindCSS |
| **Temps réel** | Django Channels, WebSockets |
| **Tâches asynchrones** | Celery, Redis |
| **Formulaires** | Crispy Forms, Bootstrap 5 |

---

## 👥 Rôles Utilisateurs

Le système implémente **5 rôles distincts** avec des permissions spécifiques :

| Rôle | Description | Permissions Clés |
|------|-------------|------------------|
| **Administrateur** | Gestionnaire du système | Accès complet, validation des réservations, gestion des utilisateurs, création de filières |
| **Enseignant** | Corps professoral | Consulter emplois du temps, réserver des salles, voir son planning personnel |
| **Étudiant** | Étudiants inscrits | Consulter emplois du temps de son groupe, télécharger son EDT |
| **Association** | Clubs et associations | Réserver des salles pour événements (après approbation admin) |
| **Invité** | Visiteurs | Accès aux pages publiques, consultation des filières |

---

## 📊 Modèles de Données

### Application `accounts` (Authentification)

| Modèle | Description |
|--------|-------------|
| `User` | Utilisateur personnalisé avec rôle, photo de profil |
| `Teacher` | Profil enseignant (département, matricule, spécialité) |
| `Student` | Profil étudiant (numéro étudiant, groupe) |
| `Association` | Profil association (description, statut d'approbation) |

### Application `core` (Données de Base)

| Modèle | Description |
|--------|-------------|
| `Room` | Salles (type, capacité, bâtiment, équipements) |
| `Program` | Filières académiques (code, département, niveau, chef de filière) |
| `Group` | Groupes d'étudiants par filière avec capacité |
| `Equipment` | Équipements des salles (projecteur, tableau, etc.) |
| `ContactMessage` | Messages de contact avec suivi de statut |

### Application `scheduling` (Planification)

| Modèle | Description |
|--------|-------------|
| `Session` | Séances de cours (CM, TD, TP, Examen) |
| `Timetable` | Emplois du temps par filière et semestre |
| `TimeSlot` | Créneaux horaires prédéfinis (9h-18h) |
| `Subject` | Matières avec heures requises et enseignant |
| `RoomReservationRequest` | Demandes de réservation (ponctuelle ou hebdomadaire) |
| `TimetableEntry` | Entrées dans l'emploi du temps |

### Application `notifications`

| Modèle | Description |
|--------|-------------|
| `Notification` | Notifications avec 17+ types, priorité, statut lecture |

---

## 🔧 Fonctionnalités Principales

### 1. Gestion des Emplois du Temps

- ✅ Création manuelle et automatique d'emplois du temps
- ✅ Affichage en grille hebdomadaire avec codes couleur (CM/TD/TP)
- ✅ Détection automatique des conflits (salle, enseignant, groupe)
- ✅ Vue par enseignant pour l'administrateur
- ✅ Export et impression des emplois du temps
- ✅ Filtrage par filière, semestre et année universitaire
- ✅ **Alignement Maître** : Synchronisation parfaite entre la vue Admin et Utilisateur (Drafts inclus)

### 2. Système de Réservation de Salles

- ✅ Formulaire de réservation avec calendrier interactif
- ✅ **Salle en premier** - Sélection prioritaire de la salle
- ✅ **Filière optionnelle** - Possibilité de réserver sans filière
- ✅ Vérification de disponibilité en temps réel
- ✅ Support des réservations récurrentes (hebdomadaires)
- ✅ Workflow d'approbation par l'administrateur
- ✅ Notifications automatiques (demande, approbation, rejet)

### 3. Gestion des Filières (Programmes)

- ✅ Création de filières avec informations complètes
- ✅ **Création automatique de groupes** lors de la création d'une filière
- ✅ Spécification du nombre de groupes et capacité par groupe
- ✅ Attribution d'un chef de filière (optionnel)
- ✅ Catalogue consultable par tous les utilisateurs
- ✅ Bouton "Créer une Filière" visible pour les admins

### 4. Gestion des Salles

- ✅ Catalogue complet avec filtres (type, capacité, équipements)
- ✅ Affichage du statut en temps réel (disponible, occupée)
- ✅ Vue détaillée avec timeline journalière
- ✅ Création en masse de salles

### 5. Système de Notifications

- ✅ Notifications en temps réel via WebSocket
- ✅ Badge de compteur non-lu dans la navbar
- ✅ 17+ types de notifications (approbation, rejet, examen, rappel séance)
- ✅ Notifications automatiques pour les cours à venir
- ✅ Historique complet des notifications

### 6. Tableau de Bord

- ✅ Dashboards personnalisés par rôle
- ✅ Statistiques et métriques clés
- ✅ Actions rapides contextuelles
- ✅ Calendrier des événements
- ✅ Vue de l'emploi du temps personnel (enseignants)

### 7. Expérience Utilisateur (UX)

- ✅ **Mode Sombre Complet** : Support total du thème sombre sur toutes les pages (profil, formulaires, tableaux)
- ✅ **Interface Scalable** : Adaptation intelligente de l'échelle (zoom 80%) pour une densité d'information optimale
- ✅ **Navigation Unifiée** : Redirections intelligentes et menus contextuels cohérents

---

## 🚀 Installation et Démarrage

### Prérequis

- Python 3.11+
- pip (gestionnaire de paquets Python)
- MySQL ou SQLite
- Git

### Étapes d'Installation

```bash
# 1. Cloner le repository
git clone https://github.com/votre-repo/fsttime.git
cd fsttime

# 2. Créer un environnement virtuel
python -m venv .venv

# 3. Activer l'environnement virtuel
# Windows:
.venv\Scripts\Activate.ps1
# Linux/Mac:
source .venv/bin/activate

# 4. Installer les dépendances
pip install -r requirements.txt

# 5. Configurer la base de données (optionnel - modifier config/settings.py)
# Par défaut: SQLite pour le développement

# 6. Appliquer les migrations
python manage.py migrate

# 7. Créer un superutilisateur
python manage.py createsuperuser

# 8. Charger les données de test (optionnel)
python manage.py seed_test_data

# 9. Lancer le serveur de développement
python manage.py runserver
```

### Accès à l'Application

- **Application** : http://127.0.0.1:8000/
- **Administration Django** : http://127.0.0.1:8000/admin/
- **Filières** : http://127.0.0.1:8000/programs/
- **Salles** : http://127.0.0.1:8000/rooms/

---

## 📁 Dépendances Principales

```txt
Django>=5.0              # Framework web principal
mysqlclient>=2.1         # Driver MySQL
Pillow>=10.0             # Traitement d'images
reportlab>=4.0           # Génération de PDF
openpyxl>=3.1            # Export Excel
channels>=4.0            # WebSockets
channels-redis>=4.1      # Backend Redis pour Channels
daphne>=4.0              # Serveur ASGI
redis>=5.0               # Cache et messaging
celery>=5.3              # Tâches asynchrones
django-crispy-forms>=2.1 # Formulaires élégants
crispy-bootstrap5>=2.0   # Template pack Bootstrap 5
django-widget-tweaks>=1.5 # Personnalisation de widgets
```

---

## 🎨 Interface Utilisateur

### Design System

- **Style** : Glassmorphism moderne avec effets de transparence et flou
- **Couleurs** : Palette violet/bleu avec gradients élégants
- **Typographie** : Inter, Poppins (Google Fonts)
- **Responsive** : Adaptatif mobile, tablette, desktop
- **Animations** : Transitions fluides et micro-interactions
- **Dark Mode** : Thème sombre "Glassmorphism" complet respectant les préférences système

### Pages Principales

| Page | URL | Description |
|------|-----|-------------|
| Accueil | `/` | Landing page publique |
| Connexion | `/accounts/login/` | Authentification |
| Inscription | `/accounts/register/` | Création de compte (enseignant, étudiant, association) |
| Tableau de bord | `/accounts/dashboard/` | Dashboard personnalisé par rôle |
| Emplois du temps | `/scheduling/timetables/` | Liste des EDT |
| EDT par Enseignant | `/scheduling/admin/teacher-timetable/` | Vue admin des EDT enseignants |
| Salles | `/rooms/` | Catalogue des salles |
| Filières | `/programs/` | Liste des filières avec bouton création (admin) |
| Réservations | `/scheduling/teacher/reservation/` | Formulaire de réservation |
| Notifications | `/notifications/` | Centre de notifications |
| Contact | `/contact/` | Formulaire de contact |

---

- ✅ **RBAC strict** : Contrôle d'accès granulaire sur les APIs de planification
- ✅ **Validation croisée** : Vérification des conflits en temps réel

---

## 📈 Créneaux Horaires

Le système utilise 5 créneaux fixes par jour :

| Créneau | Horaire | Durée |
|---------|---------|-------|
| 1 | 09:00 - 10:30 | 1h30 |
| 2 | 10:45 - 12:15 | 1h30 |
| 3 | 12:30 - 14:00 | 1h30 |
| 4 | 14:15 - 15:45 | 1h30 |
| 5 | 16:00 - 17:30 | 1h30 |

**Jours ouvrables** : Lundi au Samedi (Dimanche exclu)

---

## 🧪 Tests

```bash
# Exécuter tous les tests
python manage.py test

# Tests avec couverture
coverage run manage.py test
coverage report

# Tests d'une application spécifique
python manage.py test apps.scheduling
```

---

## 📝 Configuration

Les paramètres principaux se trouvent dans `config/settings.py` :

```python
# Langue et fuseau horaire
LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'Europe/Paris'

# Heures de travail
WORKING_HOURS_START = 9   # 9h
WORKING_HOURS_END = 18    # 18h
WORKING_DAYS = [1, 2, 3, 4, 5, 6]  # Lundi à Samedi

# Base de données
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'fsttime_db',
        # ...
    }
}
```

---

## 📦 Commandes de Gestion

```bash
# Créer les créneaux horaires par défaut
python manage.py seed_timeslots

# Charger des données de test
python manage.py seed_test_data

# Collecter les fichiers statiques (production)
python manage.py collectstatic

# Créer un superutilisateur
python manage.py createsuperuser

## 🛠️ Scripts d'Utilité

| Script | Description |
|--------|-------------|
| `inspect_program.py` | Analyse les sessions et groupes d'un programme |
| `update_student_programs.py` | Migre les données de filière pour les étudiants |
| `verify_alignment.py` | Vérifie l'alignement des emplois du temps (Master Draft) |
```

---

## 👨‍💻 Équipe de Développement

Ce projet a été développé dans le cadre d'un projet universitaire à la **Faculté des Sciences et Techniques (FST)**.

---

## 📄 Licence

Ce projet est sous licence MIT. Voir le fichier `LICENSE` pour plus de détails.

---

## 🙏 Remerciements

- **Django Software Foundation** pour le framework Django
- **Tailwind Labs** pour TailwindCSS
- **Font Awesome** pour les icônes
- **Google Fonts** pour la typographie (Inter, Poppins)

---

## 📞 Contact

Pour toute question ou suggestion, utilisez le formulaire de contact intégré à l'application ou contactez l'équipe de développement.

---

*Dernière mise à jour : Février 2026*
