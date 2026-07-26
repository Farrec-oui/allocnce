"""Tests des endpoints /admin.

Base SQLite en mémoire dédiée : ces tests ne touchent ni la base de
développement ni les PDF externes du dossier workflow/.
"""
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import Base, get_db
from main import app
from models import Allocation, User
from services.auth import create_access_token, get_password_hash


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(db_session):
    app.dependency_overrides[get_db] = lambda: db_session
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _make_user(db, email, role="user", name=None, active=True):
    user = User(
        email=email,
        hashed_password=get_password_hash("motdepasse1"),
        full_name=name or email.split("@")[0].title(),
        role=role,
        is_active=active,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _auth(user):
    token = create_access_token({"sub": str(user.id), "role": user.role})
    return {"Authorization": f"Bearer {token}"}


def _make_alloc(db, user, label="Alloc", alloc_type="creation", date="27JUN26", created_at=None):
    alloc = Allocation(
        date=date, label=label, type=alloc_type,
        user_id=user.id if user else None,
        highlight_color_index=0, highlights_json=[], changes_count=0,
        created_at=created_at or datetime.utcnow(),
    )
    db.add(alloc)
    db.commit()
    db.refresh(alloc)
    return alloc


@pytest.fixture
def admin(db_session):
    return _make_user(db_session, "admin@test.fr", role="admin", name="Admin Test")


@pytest.fixture
def regular(db_session):
    return _make_user(db_session, "user@test.fr", role="user", name="User Test")


# ---------------------------------------------------------------------------
# Contrôle d'accès
# ---------------------------------------------------------------------------

class TestAccessControl:
    ADMIN_GET = ["/admin/users", "/admin/stats", "/admin/allocations"]

    @pytest.mark.parametrize("path", ADMIN_GET)
    def test_non_admin_recoit_403(self, client, regular, path):
        assert client.get(path, headers=_auth(regular)).status_code == 403

    @pytest.mark.parametrize("path", ADMIN_GET)
    def test_sans_token_recoit_401(self, client, path):
        assert client.get(path).status_code == 401

    def test_admin_autorise(self, client, admin):
        assert client.get("/admin/users", headers=_auth(admin)).status_code == 200

    def test_non_admin_ne_peut_pas_creer_de_compte(self, client, regular):
        resp = client.post("/admin/users", headers=_auth(regular), json={
            "email": "x@test.fr", "password": "motdepasse1",
            "full_name": "X", "role": "admin",
        })
        assert resp.status_code == 403

    def test_compte_desactive_recoit_403(self, client, db_session):
        admin = _make_user(db_session, "off@test.fr", role="admin", active=False)
        assert client.get("/admin/users", headers=_auth(admin)).status_code == 403


# ---------------------------------------------------------------------------
# Garde-fous anti auto-verrouillage
# ---------------------------------------------------------------------------

class TestSelfLockout:
    def test_changer_son_propre_role_refuse(self, client, admin):
        resp = client.patch(f"/admin/users/{admin.id}", headers=_auth(admin),
                            json={"role": "user"})
        assert resp.status_code == 400

    def test_se_desactiver_via_patch_refuse(self, client, admin):
        resp = client.patch(f"/admin/users/{admin.id}", headers=_auth(admin),
                            json={"is_active": False})
        assert resp.status_code == 400

    def test_se_desactiver_via_delete_refuse(self, client, admin):
        resp = client.delete(f"/admin/users/{admin.id}", headers=_auth(admin))
        assert resp.status_code == 400

    def test_admin_reste_actif_apres_tentative(self, client, db_session, admin):
        client.delete(f"/admin/users/{admin.id}", headers=_auth(admin))
        db_session.refresh(admin)
        assert admin.is_active is True
        assert admin.role == "admin"

    def test_renommer_son_propre_compte_autorise(self, client, admin):
        resp = client.patch(f"/admin/users/{admin.id}", headers=_auth(admin),
                            json={"full_name": "Nouveau Nom"})
        assert resp.status_code == 200
        assert resp.json()["full_name"] == "Nouveau Nom"


# ---------------------------------------------------------------------------
# Création de comptes
# ---------------------------------------------------------------------------

class TestCreateUser:
    def test_creation_reussie(self, client, admin):
        resp = client.post("/admin/users", headers=_auth(admin), json={
            "email": "nouveau@test.fr", "password": "motdepasse1",
            "full_name": "Nouveau", "role": "user",
        })
        assert resp.status_code == 201
        assert resp.json()["email"] == "nouveau@test.fr"
        assert resp.json()["alloc_count"] == 0

    def test_email_duplique_409(self, client, admin, regular):
        resp = client.post("/admin/users", headers=_auth(admin), json={
            "email": regular.email, "password": "motdepasse1",
            "full_name": "Doublon", "role": "user",
        })
        assert resp.status_code == 409

    def test_email_duplique_insensible_a_la_casse(self, client, admin, regular):
        resp = client.post("/admin/users", headers=_auth(admin), json={
            "email": regular.email.upper(), "password": "motdepasse1",
            "full_name": "Doublon", "role": "user",
        })
        assert resp.status_code == 409

    def test_mot_de_passe_hache(self, client, db_session, admin):
        client.post("/admin/users", headers=_auth(admin), json={
            "email": "hash@test.fr", "password": "motdepasse1",
            "full_name": "Hash", "role": "user",
        })
        user = db_session.query(User).filter(User.email == "hash@test.fr").first()
        assert user.hashed_password != "motdepasse1"
        assert user.hashed_password.startswith("$2")


# ---------------------------------------------------------------------------
# Désactivation = suppression douce
# ---------------------------------------------------------------------------

class TestSoftDelete:
    def test_delete_ne_supprime_pas_la_ligne(self, client, db_session, admin, regular):
        assert client.delete(f"/admin/users/{regular.id}", headers=_auth(admin)).status_code == 200
        still_there = db_session.query(User).filter(User.id == regular.id).first()
        assert still_there is not None
        assert still_there.is_active is False

    def test_reactivation(self, client, admin, regular):
        client.delete(f"/admin/users/{regular.id}", headers=_auth(admin))
        resp = client.patch(f"/admin/users/{regular.id}", headers=_auth(admin),
                            json={"is_active": True})
        assert resp.json()["is_active"] is True

    def test_utilisateur_inconnu_404(self, client, admin):
        assert client.delete("/admin/users/99999", headers=_auth(admin)).status_code == 404


# ---------------------------------------------------------------------------
# alloc_count
# ---------------------------------------------------------------------------

class TestAllocCount:
    def test_comptage_par_utilisateur(self, client, db_session, admin, regular):
        for i in range(3):
            _make_alloc(db_session, regular, label=f"A{i}")
        _make_alloc(db_session, admin, label="Admin1")

        rows = {u["id"]: u["alloc_count"] for u in client.get("/admin/users", headers=_auth(admin)).json()}
        assert rows[regular.id] == 3
        assert rows[admin.id] == 1

    def test_zero_sans_allocation(self, client, admin, regular):
        rows = {u["id"]: u["alloc_count"] for u in client.get("/admin/users", headers=_auth(admin)).json()}
        assert rows[regular.id] == 0

    def test_orphelines_non_comptees(self, client, db_session, admin):
        _make_alloc(db_session, None, label="Orpheline")
        rows = {u["id"]: u["alloc_count"] for u in client.get("/admin/users", headers=_auth(admin)).json()}
        assert rows[admin.id] == 0


# ---------------------------------------------------------------------------
# Statistiques
# ---------------------------------------------------------------------------

class TestStats:
    def test_totaux(self, client, db_session, admin, regular):
        _make_alloc(db_session, regular, alloc_type="creation")
        _make_alloc(db_session, regular, alloc_type="maj")
        stats = client.get("/admin/stats", headers=_auth(admin)).json()
        assert stats["total_users"] == 2
        assert stats["active_users"] == 2
        assert stats["total_allocs"] == 2

    def test_repartition_par_type(self, client, db_session, admin, regular):
        _make_alloc(db_session, regular, alloc_type="creation")
        _make_alloc(db_session, regular, alloc_type="creation")
        _make_alloc(db_session, regular, alloc_type="prealloc")
        by_type = client.get("/admin/stats", headers=_auth(admin)).json()["allocs_by_type"]
        assert by_type["creation"] == 2
        assert by_type["prealloc"] == 1
        assert by_type["maj"] == 0

    def test_fenetre_7_jours(self, client, db_session, admin, regular):
        _make_alloc(db_session, regular, label="recente")
        _make_alloc(db_session, regular, label="vieille",
                    created_at=datetime.utcnow() - timedelta(days=30))
        stats = client.get("/admin/stats", headers=_auth(admin)).json()
        assert stats["total_allocs"] == 2
        assert stats["allocs_last_7_days"] == 1

    def test_comptes_desactives_exclus_des_actifs(self, client, db_session, admin):
        _make_user(db_session, "off@test.fr", active=False)
        stats = client.get("/admin/stats", headers=_auth(admin)).json()
        assert stats["total_users"] == 2
        assert stats["active_users"] == 1

    def test_top_users_trie(self, client, db_session, admin, regular):
        for i in range(4):
            _make_alloc(db_session, regular, label=f"R{i}")
        _make_alloc(db_session, admin, label="A0")
        top = client.get("/admin/stats", headers=_auth(admin)).json()["top_users"]
        assert top[0]["email"] == regular.email
        assert top[0]["alloc_count"] == 4
        assert len(top) <= 5


# ---------------------------------------------------------------------------
# Listing et suppression d'allocations
# ---------------------------------------------------------------------------

class TestAdminAllocations:
    def test_voit_les_allocations_de_tous(self, client, db_session, admin, regular):
        _make_alloc(db_session, regular, label="DeUser")
        _make_alloc(db_session, admin, label="DeAdmin")
        data = client.get("/admin/allocations", headers=_auth(admin)).json()
        assert data["total"] == 2
        assert {i["label"] for i in data["items"]} == {"DeUser", "DeAdmin"}

    def test_proprietaire_renseigne(self, client, db_session, admin, regular):
        _make_alloc(db_session, regular, label="DeUser")
        item = client.get("/admin/allocations", headers=_auth(admin)).json()["items"][0]
        assert item["user_email"] == regular.email
        assert item["user_name"] == regular.full_name

    def test_filtre_par_utilisateur(self, client, db_session, admin, regular):
        _make_alloc(db_session, regular, label="DeUser")
        _make_alloc(db_session, admin, label="DeAdmin")
        data = client.get(f"/admin/allocations?user_id={regular.id}", headers=_auth(admin)).json()
        assert data["total"] == 1
        assert data["items"][0]["label"] == "DeUser"

    def test_filtre_par_date(self, client, db_session, admin, regular):
        _make_alloc(db_session, regular, label="Juin", date="27JUN26")
        _make_alloc(db_session, regular, label="Juillet", date="25JUL26")
        data = client.get("/admin/allocations?date=25JUL26", headers=_auth(admin)).json()
        assert data["total"] == 1
        assert data["items"][0]["label"] == "Juillet"

    def test_pagination(self, client, db_session, admin, regular):
        for i in range(5):
            _make_alloc(db_session, regular, label=f"A{i}")
        data = client.get("/admin/allocations?limit=2&offset=0", headers=_auth(admin)).json()
        assert data["total"] == 5
        assert len(data["items"]) == 2
        page2 = client.get("/admin/allocations?limit=2&offset=2", headers=_auth(admin)).json()
        assert {i["label"] for i in page2["items"]}.isdisjoint({i["label"] for i in data["items"]})

    def test_allocation_orpheline_listee(self, client, db_session, admin):
        _make_alloc(db_session, None, label="Orpheline")
        item = client.get("/admin/allocations", headers=_auth(admin)).json()["items"][0]
        assert item["user_email"] is None

    def test_suppression(self, client, db_session, admin, regular):
        alloc = _make_alloc(db_session, regular, label="ASupprimer")
        assert client.delete(f"/admin/allocations/{alloc.id}", headers=_auth(admin)).status_code == 204
        assert db_session.query(Allocation).filter(Allocation.id == alloc.id).first() is None

    def test_suppression_refusee_au_non_admin(self, client, db_session, regular):
        alloc = _make_alloc(db_session, regular, label="Aie")
        assert client.delete(f"/admin/allocations/{alloc.id}", headers=_auth(regular)).status_code == 403
        assert db_session.query(Allocation).filter(Allocation.id == alloc.id).first() is not None

    def test_suppression_inconnue_404(self, client, admin):
        assert client.delete("/admin/allocations/99999", headers=_auth(admin)).status_code == 404


# ---------------------------------------------------------------------------
# Le cloisonnement par utilisateur reste intact
# ---------------------------------------------------------------------------

class TestIsolationPreserved:
    """Les pouvoirs admin vivent dans /admin/* : les routes ordinaires
    /allocations/* ne doivent accorder aucune dérogation."""

    def test_utilisateur_ne_voit_pas_les_allocations_des_autres(self, client, db_session, admin, regular):
        alloc = _make_alloc(db_session, admin, label="PrivéeAdmin")
        assert client.get(f"/allocations/{alloc.id}", headers=_auth(regular)).status_code == 404

    def test_utilisateur_ne_peut_pas_supprimer_celles_des_autres(self, client, db_session, admin, regular):
        alloc = _make_alloc(db_session, admin, label="PrivéeAdmin")
        assert client.delete(f"/allocations/{alloc.id}", headers=_auth(regular)).status_code == 404
        assert db_session.query(Allocation).filter(Allocation.id == alloc.id).first() is not None

    def test_liste_ordinaire_reste_cloisonnee_meme_pour_un_admin(self, client, db_session, admin, regular):
        _make_alloc(db_session, regular, label="DeUser")
        groups = client.get("/allocations/", headers=_auth(admin)).json()
        assert groups == []
