# SAAJD — Conception des interfaces

## 1. Objet et périmètre

Ce document décrit l'expérience utilisateur cible du Système d'Analyse Assistée de Dossiers Judiciaires (SAAJD) : organisation des écrans, navigation, parcours par rôle, présentation des analyses, états de l'interface et règles visuelles.

Le dépôt contient actuellement le backend FastAPI et son contrat OpenAPI, mais aucune interface web. Les écrans ci-dessous sont donc une spécification de conception, pas une description d'écrans déjà implémentés. Les parcours s'appuient sur les routes de `backend/api.yaml` et signalent explicitement les éléments qui nécessiteront une évolution de l'API.

Le système est une aide à la conformité procédurale. Il ne désigne jamais de coupable, ne prédit pas une décision, ne produit aucun score de culpabilité et ne remplace ni l'avocat, ni l'enquêteur, ni le magistrat.

## 2. Utilisateurs et droits d'accès

| Rôle | Besoins principaux | Accès d'interface |
|---|---|---|
| Enquêteur | Ouvrir ses dossiers, déposer les pièces, suivre les extractions, lancer une analyse, consulter les alertes et exporter le rapport. | Créer et modifier ses dossiers, gérer les pièces de ses dossiers, consulter ses analyses. |
| Magistrat | Consulter les dossiers et analyses, examiner les sources et pièces, télécharger les rapports. | Consultation et export ; aucune action de modification dans l'interface. |
| Administrateur | Gérer les comptes et leurs rôles, désactiver les comptes, consulter l'audit et les métriques, demander la réindexation constitutionnelle. | Accès aux écrans d'administration. |

L'interface masque les commandes non autorisées, mais ne considère jamais ce masquage comme une protection : l'API reste l'autorité pour les contrôles d'accès. Les données visibles sont limitées par les autorisations du serveur. Un enquêteur ne voit que ses dossiers ; les rôles habilités à la consultation peuvent accéder aux autres dossiers conformément aux règles backend.

## 3. Architecture de navigation

### Navigation commune

- Barre supérieure sobre : nom SAAJD, environnement courant, état des services, utilisateur connecté et menu de session.
- Navigation principale persistante sur grand écran, repliée en menu sur mobile.
- Zone centrale à largeur de lecture confortable, organisée en tableaux, formulaires et panneaux non décoratifs.
- Bandeau de présomption d'innocence visible dans toute vue qui affiche une analyse ou un export.
- Fil d'Ariane pour les vues de dossier, pièce et analyse.
- Les actions principales restent visibles et nommées ; les actions secondaires sont dans un menu dédié.

### Entrées de navigation par rôle

**Enquêteur :** `Tableau de bord`, `Dossiers`, `Créer un dossier`, `Mon compte`.

**Magistrat :** `Dossiers`, `Analyses consultées`, `Mon compte`. La liste « Analyses consultées » peut être omise tant que l'API ne fournit pas de recherche ou d'historique par utilisateur magistrat.

**Administrateur :** `Vue d'ensemble`, `Dossiers`, `Utilisateurs`, `Journal d'audit`, `Indicateurs`, `Constitution`, `Mon compte`.

La navigation ne doit pas faire croire qu'un écran existe si l'API ne fournit pas encore ses données. Les écrans marqués « à compléter côté API » dans ce document sont des objectifs de conception et des éléments de backlog.

## 4. Écrans

### 4.1 Connexion

**Objectif :** ouvrir une session sans exposer de détails techniques.

**Contenu :** logo ou nom textuel SAAJD, champ e-mail, champ mot de passe avec commande afficher/masquer, bouton `Se connecter`, lien de support fourni par l'organisation.

**Comportement :**

- Validation locale du format e-mail et du champ mot de passe ; validation serveur finale.
- Pendant l'envoi, désactiver le bouton et afficher un indicateur dans celui-ci.
- En cas d'identifiants refusés, afficher un message générique sans préciser si le compte existe.
- En cas de service indisponible, expliquer qu'une connexion est temporairement impossible et proposer une nouvelle tentative.
- Ne jamais afficher ni journaliser le mot de passe ou les jetons.

**API :** `POST /api/v1/auth/login`. Le renouvellement et la révocation de session utilisent `POST /api/v1/auth/refresh` et `POST /api/v1/auth/logout`.

### 4.2 Tableau de bord enquêteur

**Objectif :** reprendre rapidement un dossier en cours et repérer le travail restant.

**Contenu :**

- Liste des dossiers récents, identifiant, infraction déclarée, date d'ouverture, statut et dernière activité disponible.
- Filtre par statut et type d'infraction ; recherche par numéro de dossier si un endpoint de recherche est disponible.
- Compteurs sobres : dossiers ouverts, analyses en cours, extractions en attente et pièces en échec.
- Action principale `Créer un dossier`.

**Actions :** ouvrir un dossier, créer un dossier, reprendre une analyse terminée ou en erreur.

**API disponible :** `GET /api/v1/dossiers` avec `statut`, `infraction_type`, `page`, `size`. Les compteurs, la dernière activité et la recherche textuelle ne sont pas fournis directement par l'API actuelle ; les calculer côté client uniquement à partir d'une liste complète n'est pas fiable.

### 4.3 Liste des dossiers

**Objectif :** retrouver et comparer les dossiers accessibles.

**Colonnes :** numéro, infraction, date d'ouverture, statut, actions. Sur mobile, afficher chaque entrée sous forme de ligne compacte avec les métadonnées secondaires repliables.

**Commandes :** filtres de statut (`OUVERT`, `EN_ANALYSE`, `CLOS`), filtre de type d'infraction, pagination précédente/suivante, bouton de création selon le rôle.

**États :** chargement sous forme de lignes squelettes ; liste vide avec action adaptée au rôle ; erreur avec reprise ; résultats filtrés vides avec commande `Effacer les filtres`.

**API :** `GET /api/v1/dossiers`, `POST /api/v1/dossiers`.

### 4.4 Création et modification d'un dossier

**Objectif :** enregistrer uniquement les informations de base, puis compléter les pièces au sein du dossier.

**Champs :**

- Numéro de dossier, requis.
- Type d'infraction déclaré, requis ; ce champ décrit la qualification enregistrée et n'est pas une conclusion du système.
- Date d'ouverture, préremplie avec la date locale, modifiable.
- Métadonnées complémentaires, uniquement si les champs validés par le métier sont définis.

**Comportement :** validation en ligne, erreurs associées aux champs, confirmation de création, annulation avec avertissement si des changements non enregistrés sont présents. Les statuts ne sont jamais présentés comme une décision judiciaire.

**API :** `POST /api/v1/dossiers`, `PATCH /api/v1/dossiers/{dossier_id}`. `POST /api/v1/dossiers/{dossier_id}/close` demande une confirmation explicite.

### 4.5 Détail d'un dossier

**En-tête :** numéro de dossier, type d'infraction déclaré, date d'ouverture, statut, propriétaire ou créateur si autorisé.

**Sections ou onglets :**

1. `Résumé` : synthèse des pièces, état des extractions, dernière analyse et avertissements importants.
2. `Pièces` : dépôt, liste, aperçu ou téléchargement, type reconnu, date, hash et état d'extraction.
3. `Analyses` : historique des analyses, état, date, accès au rapport.
4. `Journal` : activité liée au dossier uniquement si une API dédiée est mise en place.

**Actions enquêteur :** ajouter une pièce, supprimer une pièce avec confirmation, modifier le dossier, lancer une analyse lorsque les extractions sont prêtes, clore le dossier.

**Actions magistrat :** consulter les pièces, ouvrir les rapports et télécharger les documents, sans commandes de modification.

**Actions administrateur :** consulter le dossier selon les droits ; les commandes destructrices restent soumises aux règles métier.

**API disponible :** détail `GET /api/v1/dossiers/{dossier_id}`, modification, clôture, endpoints de pièces et d'analyses associés. L'API de détail renvoie actuellement uniquement `DossierRead`, pas les pièces et analyses intégrées ; l'écran doit charger ces ressources séparément.

### 4.6 Dépôt et suivi des pièces

**Zone de dépôt :** bouton `Ajouter des pièces` ouvrant un sélecteur de fichiers, avec prise en charge du glisser-déposer sur ordinateur. Afficher les formats PDF, DOCX, TXT, JPEG, PNG et TIFF, ainsi que la limite de taille configurée.

**Liste des pièces :** nom du fichier, type classé, format, taille, hash SHA-256, date d'envoi et état : `En attente`, `Extraction en cours`, `Terminée`, `Échec`.

**Comportement :** progression de l'envoi, rejet explicite des formats ou tailles invalides, possibilité de réessayer après échec, aucune prétention que l'OCR a réussi avant réception du résultat worker. La suppression indique clairement son effet et demande confirmation.

**API :** `POST /api/v1/dossiers/{dossier_id}/documents` (multipart `file`), `GET /api/v1/dossiers/{dossier_id}/documents`, `GET /api/v1/documents/{document_id}`, `GET /api/v1/documents/{document_id}/download`, `DELETE /api/v1/documents/{document_id}`.

**Aperçu de document :** ouvrir le document dans un panneau ou un nouvel onglet sécurisé à partir de l'URL présignée ; l'URL de téléchargement est temporaire et ne doit pas être conservée comme un lien permanent.

### 4.7 Lancement et suivi d'analyse

**Avant lancement :** afficher le nombre de pièces, l'état d'extraction et les éventuelles pièces manquantes détectées. Expliquer qu'une analyse peut échouer si le registre constitutionnel ou le fournisseur IA est indisponible. Le bouton `Lancer l'analyse` est désactivé si le dossier est clos ou sans pièce.

**Après lancement :** afficher un état non bloquant `En attente` puis `En cours`, actualisé par interrogation périodique de `GET /api/v1/analyses/{analyse_id}`. Ne pas simuler une barre de progression chiffrée si le serveur ne fournit pas cette progression.

**États d'échec :** afficher le message d'erreur renvoyé et une action de nouvelle tentative quand elle est permise. Un échec est distinct d'une conclusion sur le dossier.

**API :** `POST /api/v1/dossiers/{dossier_id}/analyses`, `GET /api/v1/analyses/{analyse_id}`, `GET /api/v1/dossiers/{dossier_id}/analyses`.

### 4.8 Rapport d'analyse

Le rapport est une page de lecture hiérarchisée, avec le bandeau légal persistant en tête :

> Ce rapport est un outil d'aide. Il ne constitue ni une mise en cause ni un jugement. La présomption d'innocence prévaut. Toute appréciation finale appartient à l'autorité compétente.

Ordre des blocs :

1. Identifiants du dossier et de l'analyse, date et état du rapport.
2. Synthèse quantitative : pièces analysées, contrôles signalés, pièces manquantes, indices mentionnés ; ne pas créer de score de risque ou de culpabilité.
3. Contrôles procéduraux : gravité, faits documentés, conséquence formulée au conditionnel, référence constitutionnelle exacte, lien vers la pièce source lorsque disponible.
4. Pièces manquantes : pièce recherchée, justification, source du besoin et piste de collecte si elle est réellement documentée.
5. Éléments à examiner : toujours appelés « indices » ou « déclarations », avec référence au document ; aucun libellé accusatoire.
6. Pistes à explorer : action concrète, justification et référence légale vérifiée.
7. Recommandation finale limitée à la complétude et aux vérifications procédurales.
8. Traçabilité : hash SHA-256, auteur et date d'export.

Les références sont affichées avec le numéro, l'alinéa lorsqu'il est présent, le texte canonique et la source. Une référence introuvable ou non vérifiée ne doit pas être maquillée en citation.

**Actions :** exporter PDF, exporter JSON, revenir au dossier. Le bouton `Imprimer` peut utiliser la mise en page imprimable du rapport si elle est réalisée côté interface.

**API :** exports `GET /api/v1/analyses/{analyse_id}/report.pdf` et `GET /api/v1/analyses/{analyse_id}/report.json`. L'API actuelle ne fournit pas de lien de source-page calculé automatiquement pour chaque observation : ne montrer un numéro de page que si l'extraction le fournit réellement.

### 4.9 Gestion des utilisateurs (administrateur)

**Liste :** nom complet, e-mail, rôle, état actif, date de création. Recherche et filtre de rôle peuvent être ajoutés côté interface après réception de la liste complète.

**Création :** e-mail, nom complet, rôle (`ENQUETEUR`, `MAGISTRAT`, `ADMIN`), mot de passe initial respectant au moins 12 caractères. Ne pas proposer la lecture ou la récupération du mot de passe.

**Actions :** modifier les informations non sensibles, changer le rôle avec confirmation, désactiver un compte avec confirmation. La désactivation ne doit pas être présentée comme une suppression définitive.

**API :** `GET /api/v1/users`, `POST /api/v1/users`, `PATCH /api/v1/users/{user_id}`, `PATCH /api/v1/users/{user_id}/role`, `DELETE /api/v1/users/{user_id}`.

### 4.10 Audit et métriques (administrateur)

**Journal d'audit :** table chronologique indiquant date, compte, action, ressource, identifiant de ressource et adresse IP si présente. Pagination. Ne jamais afficher le contenu des dossiers dans les métadonnées d'audit.

**Métriques :** nombres de dossiers, analyses et analyses en erreur, sans classement ou score de personnes.

**Réindexation constitutionnelle :** action séparée et clairement décrite, déclenchant une tâche asynchrone. Afficher l'identifiant de tâche et un état de mise en file ; la progression détaillée ne peut apparaître que si l'API fournit un endpoint de statut de tâche.

**API :** `GET /api/v1/admin/audit`, `GET /api/v1/admin/metrics`, `POST /api/v1/admin/constitution/reload`.

### 4.11 Profil et fin de session

Le menu de compte affiche le nom, l'e-mail et le rôle. Il propose `Déconnexion`. L'API fournit `GET /api/v1/auth/me` et `POST /api/v1/auth/logout`. Les jetons sont conservés selon une stratégie sécurisée définie pour le frontend ; ne pas les placer dans des paramètres d'URL ou les exposer dans les journaux navigateur.

## 5. Parcours de bout en bout

### Enquêteur : dossier jusqu'au rapport

1. Connexion.
2. Création d'un dossier avec numéro, infraction déclarée et date.
3. Dépôt de plusieurs pièces et suivi indépendant de chaque extraction.
4. Vérification des noms, types et états des pièces ; correction d'un dépôt erroné si autorisée.
5. Lancement de l'analyse dès que les extractions sont terminées.
6. Lecture du rapport, ouverture des pièces sources et distinction des faits, absences et pistes.
7. Export PDF ou JSON avec avertissement légal et empreinte.
8. Clôture du dossier si le processus métier le permet.

### Magistrat : consultation

1. Connexion avec un rôle de consultation.
2. Recherche puis ouverture d'un dossier autorisé.
3. Consultation des pièces, de l'historique d'analyse et des références.
4. Téléchargement du rapport ; aucune commande de modification ou d'analyse n'est affichée.

### Administrateur : comptes et traçabilité

1. Connexion administrateur.
2. Création et attribution du rôle adapté à chaque compte.
3. Consultation des indicateurs de service et d'activité.
4. Consultation paginée de l'audit.
5. Déclenchement de la réindexation si elle est opérable, puis suivi du résultat par le mécanisme de tâche disponible.

## 6. Système visuel

### Direction artistique

Interface de travail juridique et opérationnelle : précise, calme, dense sans surcharge. Pas de page marketing ni de grand écran d'accueil décoratif. Le premier écran après connexion est directement le tableau utile au rôle.

### Couleurs

- Fond principal clair neutre ; surfaces et séparateurs peu contrastés mais visibles.
- Texte principal presque noir, texte secondaire suffisamment contrasté.
- Accent bleu pétrole ou cyan sombre réservé aux actions et liens.
- Vert pour une opération terminée, ambre pour une vérification à effectuer, rouge pour une erreur ou une alerte critique.
- La couleur n'est jamais l'unique moyen de distinguer états ou gravités : libellé, icône et texte restent présents.
- Rouge réservé aux alertes effectives et au bandeau légal ; éviter une page entière dominée par le rouge.

### Typographie et densité

- Police de lecture robuste avec bonne couverture des caractères français ; hiérarchie régulière entre titre de page, titre de section, libellé et texte d'aide.
- Éviter les grands titres décoratifs, les majuscules prolongées et les paragraphes trop larges.
- Tables compactes avec hauteur de ligne suffisante pour conserver la lisibilité et la sélection clavier.
- Préserver accents, apostrophes, numéros d'article et textes constitutionnels sans troncature silencieuse.

### Composants

- Bouton principal nommé, bouton secondaire discret, commandes destructrices séparées et confirmées.
- Formulaires avec libellés persistants, contraintes visibles à l'avance et erreurs proches des champs.
- Tables avec en-têtes sémantiques, tri uniquement lorsqu'il correspond à un ordre serveur ou à des données chargées complètes.
- Badges de statut accompagnés de texte ; icônes avec nom accessible et infobulle si leur sens n'est pas évident.
- Panneaux ou modales uniquement pour les tâches contextualisées (confirmation de clôture, désactivation, suppression).
- Pas de cartes décoratives empilées : préférer sections pleine largeur et séparateurs.

## 7. Adaptation aux écrans et accessibilité

- Ordinateur : navigation persistante, tables complètes et panneau de détail.
- Tablette : navigation rétractable, colonnes secondaires masquables sans perdre les identifiants et actions principales.
- Mobile : navigation en tiroir, tables converties en lignes descriptives, actions principales accessibles sans défilement horizontal. Les formulaires et rapports s'empilent en une seule colonne.
- Cibles tactiles assez grandes, focus visible, ordre clavier logique et gestion du focus dans les dialogues.
- Contraste conforme au niveau AA des WCAG pour le texte courant et les éléments interactifs.
- Tout message d'état est annoncé aux technologies d'assistance ; les changements d'analyse asynchrone ne déplacent pas le focus.
- Permettre l'agrandissement du texte et respecter la préférence de réduction des animations.
- Les PDF exportés restent lisibles à l'impression et ne reposent pas seulement sur la couleur.

## 8. États transversaux et erreurs

- **Chargement :** indicateur à proximité du contenu concerné ; garder le contexte visible.
- **Vide :** expliquer pourquoi la liste est vide et proposer l'action autorisée suivante.
- **Erreur réseau/serveur :** message clair, identifiant de requête si fourni, bouton de reprise quand elle est sûre.
- **401 :** renouveler la session si possible ; sinon revenir à la connexion avec conservation du contexte non sensible.
- **403 :** expliquer que le rôle ou le périmètre n'autorise pas l'action, sans révéler de données.
- **404 :** indiquer que la ressource n'existe plus ou n'est pas accessible.
- **422 :** afficher les erreurs de validation au niveau du champ et garder les saisies valides.
- **Dépendance dégradée :** signaler l'indisponibilité sans présenter des données périmées comme actuelles ; désactiver uniquement les actions dépendantes.
- **Analyse en erreur :** montrer un statut d'échec explicite, aucun faux rapport, et l'erreur technique filtrée pour ne pas exposer secrets ou contenu sensible.

## 9. Données sensibles et garde-fous UX

- Utiliser un avertissement permanent de présomption d'innocence dans les écrans d'analyse et les exports.
- Employer les termes `indice`, `déclaration`, `élément mentionné` ou `point à vérifier`, jamais `coupable`, `criminel` ou une conclusion équivalente.
- Présenter les alertes comme des constats documentaires à examiner, pas comme une décision juridique certaine.
- Afficher la source et le texte canonique à côté de chaque référence. Si une référence manque, interrompre ou signaler l'analyse ; ne pas afficher une citation reconstruite.
- Limiter les aperçus de pièces aux utilisateurs autorisés et éviter la mise en cache publique des documents ou URL présignées.
- Ne pas inclure les noms ou le texte intégral des pièces dans notifications, URLs, analytics ou journaux client.
- Demander confirmation avant fermeture, désactivation et suppression de pièce ; préciser l'impact avant l'action.

## 10. Écarts et prérequis backend pour une interface complète

Les écrans sont conçus en fonction des routes disponibles, mais les éléments suivants sont nécessaires pour une expérience plus complète :

1. Endpoint de liste avec total, pagination explicite, recherche textuelle, tri et filtres de dates ; la liste actuelle renvoie un tableau simple.
2. Endpoint de détail dossier agrégé avec documents, analyses et dernière activité pour éviter de multiplier les appels.
3. État de tâche Celery pour suivre extraction, analyse et réindexation avec progression ou messages structurés.
4. Informations de page et provenance d'extraction pour relier chaque constat à un passage précis de la pièce.
5. Rapport cohérent entre API, interface et PDF : bandeau canonique, références exactes et hash vérifiable identique.
6. Fonction de récupération de mot de passe et politique d'expiration/sécurité des sessions si requises par le déploiement.
7. API de profil avec champs modifiables si l'utilisateur doit gérer ses propres informations.
8. Règles d'accès explicites pour le magistrat, notamment périmètre organisationnel et dossiers consultables.
9. Pagination complète, filtres temporels et export du journal d'audit.
10. Tests d'accessibilité, tests de parcours par rôle et tests responsive sur appareils cibles.

Ces éléments ne doivent pas être simulés côté client. Tant qu'ils ne sont pas fournis par le backend ou définis par le métier, l'interface doit présenter les capacités effectivement disponibles et les limites correspondantes.

## 11. Critères d'acceptation UX

- Un enquêteur peut créer un dossier, déposer plusieurs formats autorisés, suivre leur extraction et accéder au rapport lorsqu'une analyse est terminée.
- Un magistrat peut consulter uniquement les ressources permises et ne reçoit aucune action d'écriture dans son interface.
- Un administrateur peut gérer les utilisateurs et consulter les vues d'audit et de métriques protégées.
- Tous les états (chargement, vide, réussite, erreur, accès refusé, dépendance indisponible) ont un rendu et une action compréhensibles.
- Chaque analyse visible porte l'avertissement de présomption d'innocence et ne contient aucune conclusion de culpabilité.
- Les références juridiques sont traçables au registre ; l'interface n'invente pas de texte, de page source ou de progression.
- Les tâches essentielles sont utilisables au clavier, avec lecteur d'écran, et sur écran étroit sans perte d'information critique.