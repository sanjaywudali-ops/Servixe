"""Seed roles/permissions from code definitions (idempotent)."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.permissions import ALL_PERMISSIONS, ROLE_PERMISSIONS
from app.modules.identity.models import Permission, Role, RolePermission


def seed_rbac(db: Session) -> None:
    for code, desc in ALL_PERMISSIONS.items():
        if not db.get(Permission, code):
            db.add(Permission(code=code, description=desc))
    db.flush()
    for name, perms in ROLE_PERMISSIONS.items():
        role = db.scalar(select(Role).where(Role.name == name))
        if not role:
            role = Role(name=name, description=f"{name} role")
            db.add(role)
            db.flush()
        have = {rp.permission_code for rp in role.permissions}
        for p in perms - have:
            role.permissions.append(RolePermission(role_id=role.id, permission_code=p))
        for rp in list(role.permissions):
            if rp.permission_code not in perms:
                role.permissions.remove(rp)
    db.commit()
