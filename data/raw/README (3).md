# Projet RBAC avec Keycloak

Ce projet met en œuvre une politique RBAC (Role-Based Access Control) en utilisant Keycloak comme solution d'authentification et de gestion des rôles. Il s'agit d'un projet orienté cybersécurité visant à contrôler l'accès aux ressources et fonctionnalités en fonction des permissions associées aux rôles des utilisateurs.

## Objectifs du projet

- Implémenter un contrôle d'accès basé sur les rôles (RBAC) pour sécuriser l'application.
- Utiliser **Keycloak** pour gérer les utilisateurs, les rôles et les permissions.
- Protéger les routes de l'application en fonction des rôles et permissions des utilisateurs.
- Fournir une interface utilisateur simple permettant d'afficher et de gérer les données (étudiants et leurs notes).

## Fonctionnalités principales

- **Authentification sécurisée** :
    - Utilisation de Keycloak pour authentifier les utilisateurs.
    - Gestion des sessions avec `express-session` et intégration avec Keycloak.

- **Contrôle d'accès** :
    - Permissions définies par rôle (lecture, écriture, validation des données).
    - Protéger les routes sensibles en fonction des permissions de l'utilisateur.

- **Interface utilisateur** :
    - Tableau pour afficher les données des étudiants.
    - Formulaire d'ajout de nouvelles entrées (étudiants et notes).
    - Boutons pour valider les données, visibles uniquement si l'utilisateur dispose des permissions nécessaires.

- **Stockage temporaire** :
    - Utilisation de `localStorage` côté client pour stocker les données en session (simule une base de données).

## Prérequis

Avant de lancer le projet, assurez-vous d'avoir installé les outils suivants :

- [Node.js](https://nodejs.org/) (v16 ou supérieure)
- [Keycloak](https://www.keycloak.org/) (serveur de gestion des identités)

## Auteur 
- **Nom** : Jean GUIRAUD
