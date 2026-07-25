#!/usr/bin/env python
"""Crée (ou promeut) un compte administrateur.

    python create_admin.py --email admin@allocnce.fr --password XXXX --name "Admin"

Par défaut, les allocations créées avant la mise en place de
l'authentification (user_id NULL) sont rattachées à ce compte, sinon elles
resteraient invisibles pour tout le monde. Utiliser --no-claim pour l'éviter.
"""
import argparse
import getpass
import sys

from sqlalchemy import func

from database import SessionLocal
from models import Allocation, User
from services.auth import get_password_hash

MIN_PASSWORD_LEN = 8


def main() -> int:
    parser = argparse.ArgumentParser(description="Créer un compte administrateur AllocNCE")
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", help="Demandé de façon interactive si omis")
    parser.add_argument("--name", required=True, dest="full_name")
    parser.add_argument(
        "--no-claim",
        action="store_true",
        help="Ne pas rattacher les allocations orphelines à ce compte",
    )
    args = parser.parse_args()

    password = args.password or getpass.getpass("Mot de passe : ")
    if len(password) < MIN_PASSWORD_LEN:
        print(f"Erreur : le mot de passe doit faire au moins {MIN_PASSWORD_LEN} caractères.",
              file=sys.stderr)
        return 1

    email = args.email.strip().lower()
    db = SessionLocal()
    try:
        user = db.query(User).filter(func.lower(User.email) == email).first()

        if user:
            # Compte existant : on le promeut et on réinitialise son mot de passe.
            user.role = "admin"
            user.is_active = True
            user.hashed_password = get_password_hash(password)
            user.full_name = args.full_name.strip()
            action = "mis à jour (promu admin)"
        else:
            user = User(
                email=email,
                hashed_password=get_password_hash(password),
                full_name=args.full_name.strip(),
                role="admin",
                is_active=True,
            )
            db.add(user)
            action = "créé"

        db.commit()
        db.refresh(user)
        print(f"Compte admin {action} : {user.email} (id={user.id})")

        if not args.no_claim:
            orphans = db.query(Allocation).filter(Allocation.user_id.is_(None)).all()
            if orphans:
                for alloc in orphans:
                    alloc.user_id = user.id
                db.commit()
                print(f"{len(orphans)} allocation(s) orpheline(s) rattachée(s) à ce compte.")
            else:
                print("Aucune allocation orpheline à rattacher.")

        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
