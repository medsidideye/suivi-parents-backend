# API — Suivi scolaire parents

## Installation et lancement

```
py -m pip install -r requirements.txt
py -m uvicorn app.main:app --reload
```

## Première mise en route

```
py -m app.core.creer_super_admin
```

Si tu oublies un jour le mot de passe du super-admin :

```
py -m app.core.reinitialiser_super_admin
```

⚠️ Si tu avais une base de données créée avec une version précédente, supprime le
fichier suivi_parents.db avant de relancer.

## Nouveau flux — création et récupération de compte admin école, par code de vérification

Le super-admin ne définit plus le mot de passe d'un admin école. À la place :

1. **Création** : POST /ecoles/{id_ecole}/admins ne prend plus que `nom` et `email`.
   La réponse inclut un `code_verification` (6 chiffres) à communiquer à l'école —
   ce code n'est renvoyé qu'une seule fois, au moment de la création.
2. **Activation** : l'admin va sur POST /auth/admin-ecole/definir-mot-de-passe avec
   son `email`, le `code_verification` reçu, et le mot de passe de son choix. Le
   compte n'est utilisable pour se connecter qu'après cette étape.
3. **Oubli / réinitialisation** : le super-admin appelle
   POST /ecoles/admins/{id_admin}/reinitialiser-mot-de-passe, qui génère un
   **nouveau** code de vérification (l'ancien mot de passe reste valide entre-temps,
   pour ne pas bloquer l'admin avant qu'il n'ait redéfini son mot de passe). L'admin
   utilise ensuite ce nouveau code sur la même route `definir-mot-de-passe` que pour
   l'activation — le mécanisme est identique dans les deux cas.
4. GET /ecoles/{id_ecole}/admins indique pour chacun `compte_active: true/false`,
   selon qu'un mot de passe a déjà été défini.
5. Un code est à usage unique : une fois utilisé pour définir un mot de passe, il est
   effacé et ne peut plus être réutilisé.

## Gestion des mots de passe (rappel)

- **Parent** : réinitialisation par l'école (POST /admin/parents/{id}/reinitialiser-mot-de-passe,
  génère un mot de passe temporaire à 6 chiffres directement utilisable) ; changement
  volontaire une fois connecté (POST /parents/moi/changer-mot-de-passe).
- **Admin école** : voir le flux par code de vérification ci-dessus ; changement
  volontaire une fois connecté (POST /admin/moi/changer-mot-de-passe).
- **Super-admin** : script CLI en cas d'oubli ; changement volontaire une fois
  connecté (POST /ecoles/moi/changer-mot-de-passe).

## Nouveautés précédentes (rappel)

- Connexion parent par téléphone, comptes admin/super-admin par email
- Fiche élève enrichie (numéro national, RIM, numéro d'appel)
- Rattacher un enfant supplémentaire à un parent à tout moment
- Emploi du temps en bloc, absence avec matière, inscription multi-enfants

## Rôles et sécurité

- **super_admin** : crée les écoles et leurs comptes admin (sans mot de passe, avec
  code de vérification), réinitialise leurs codes, liste les écoles et leurs admins
- **admin_ecole** : gère uniquement sa propre école, cloisonnement strict (404 sur
  toute tentative concernant une autre école)
- **parent** : connexion par téléphone, ne voit que les enfants qui lui ont été
  explicitement attribués

## Base de données

SQLite par défaut. PostgreSQL en production via DATABASE_URL.
