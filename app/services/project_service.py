"""ProjectService — business logic Project (ORM, Phase 2).

Kontrak return: DTO `ProjectView` untuk tampilan (counts precomputed via
aggregate query — 17-performance.md #1/#3), objek `Project` untuk operasi
tulis. Error kontrak: validasi gagal → `raise ValueError(pesan)`.
"""
import re
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import case, delete, func, select, update

from app.extensions import db
from app.models import Project, Task, TaskStatus

HEX_COLOR_PATTERN = re.compile(r"^#[0-9A-Fa-f]{6}$")  # didefinisikan sekali (03-service.md #3)

_DEFAULT_ICON = "folder"


@dataclass(frozen=True)
class ProjectView:
    """DTO tampilan project — field display precomputed di service.

    `total_tasks`/`active_tasks`/`done_tasks`/`archived_tasks` untuk project
    root sudah MENJUMLAHKAN seluruh sub project (subtree); untuk sub project
    nilainya miliknya sendiri. `child_count` = jumlah sub project langsung.
    """
    id: int
    public_id: str
    parent_id: int | None
    parent_public_id: str | None
    parent_name: str | None
    name: str
    color: str
    icon: str  # nama ikon Font Awesome tanpa prefix, mis. "briefcase"
    archived: bool
    created_at: datetime
    child_count: int
    total_tasks: int
    active_tasks: int
    done_tasks: int
    archived_tasks: int


def _to_view(
    project: Project,
    total: int,
    active: int,
    archived_tasks: int,
    child_count: int = 0,
) -> ProjectView:
    icon = (project.icon or "").strip().removeprefix("fa-") or _DEFAULT_ICON
    parent = project.parent
    return ProjectView(
        id=project.id,
        public_id=project.public_id,
        parent_id=project.parent_id,
        parent_public_id=parent.public_id if parent else None,
        parent_name=parent.name if parent else None,
        name=project.name,
        color=project.color,
        icon=icon,
        archived=bool(project.archived),
        created_at=project.created_at,
        child_count=child_count,
        total_tasks=total,
        active_tasks=active,
        done_tasks=total - active - archived_tasks,
        archived_tasks=archived_tasks,
    )


def _counts_stmt():
    """Query aggregate project + jumlah task (1 query untuk semua project — anti N+1).

    Kolom: (Project, total, active, archived) — archived = task terarsip
    (subset dari done; invariant state machine: terarsip selalu done).
    """
    return (
        select(
            Project,
            func.count(Task.id).label("total"),
            func.coalesce(
                func.sum(case((Task.status != TaskStatus.DONE, 1), else_=0)), 0
            ).label("active"),
            func.coalesce(
                func.sum(case((Task.archived_at.is_not(None), 1), else_=0)), 0
            ).label("archived"),
        )
        .outerjoin(Task, Task.project_id == Project.id)
        .group_by(Project.id)
        .order_by(Project.created_at.desc(), Project.id.desc())
    )


class ProjectService:
    """CRUD + aturan bisnis Project."""

    # ── Read ──
    def get_all(self, include_archived: bool = False) -> list[ProjectView]:
        """Semua project (root + sub), urut terbaru — daftar datar.

        Counts root = subtree (root + seluruh sub project, termasuk yang
        diarsipkan) agar total tidak berubah hanya karena sub diarsipkan.
        `include_archived` hanya memfilter baris yang DITAMPILKAN.
        """
        rows = db.session.execute(_counts_stmt()).all()
        own = {p.id: (int(total), int(active), int(archived)) for p, total, active, archived in rows}
        child_ids: dict[int, list[int]] = {}
        for project, *_ in rows:
            if project.parent_id is not None:
                child_ids.setdefault(project.parent_id, []).append(project.id)

        views: list[ProjectView] = []
        for project, *_ in rows:
            total, active, archived = own[project.id]
            ids = child_ids.get(project.id, [])
            for child_id in ids:
                child_total, child_active, child_archived = own[child_id]
                total += child_total
                active += child_active
                archived += child_archived
            views.append(_to_view(project, total, active, archived, len(ids)))

        return views if include_archived else self._visible_branch(views)

    @staticmethod
    def _visible_branch(views: list[ProjectView]) -> list[ProjectView]:
        """Buang project terarsip DAN sub project dari parent terarsip.

        Arsip parent = sembunyikan satu cabang (tanpa menulis flag children).
        """
        visible = [v for v in views if not v.archived]
        visible_ids = {v.id for v in visible}
        return [v for v in visible if v.parent_id is None or v.parent_id in visible_ids]

    def get_roots(self, include_archived: bool = False) -> list[ProjectView]:
        """Project level 1 saja (`parent_id` NULL) — counts sudah roll-up."""
        return [v for v in self.get_all(include_archived) if v.parent_id is None]

    def get_children(self, parent_id: int, include_archived: bool = False) -> list[ProjectView]:
        """Sub project langsung milik `parent_id`, urut nama."""
        return sorted(
            (v for v in self.get_all(include_archived) if v.parent_id == parent_id),
            key=lambda v: v.name.lower(),
        )

    def get_hierarchical(self, include_archived: bool = False) -> list[ProjectView]:
        """Root diikuti sub project-nya — urutan siap pakai untuk dropdown.

        Sub project dari parent yang tersembunyi (diarsipkan) otomatis tidak
        ikut karena root-nya sudah difilter lebih dulu.
        """
        views = self.get_all(include_archived)
        by_parent: dict[int, list[ProjectView]] = {}
        for view in views:
            if view.parent_id is not None:
                by_parent.setdefault(view.parent_id, []).append(view)

        ordered: list[ProjectView] = []
        for root in (v for v in views if v.parent_id is None):
            ordered.append(root)
            ordered.extend(sorted(by_parent.get(root.id, []), key=lambda v: v.name.lower()))
        return ordered

    def _get_one(self, where) -> ProjectView | None:
        """Satu project + counts subtree-nya (2 query, bukan N+1)."""
        row = db.session.execute(_counts_stmt().where(where)).first()
        if row is None:
            return None
        project, total, active, archived = row
        total, active, archived = int(total), int(active), int(archived)
        child_rows = db.session.execute(_counts_stmt().where(Project.parent_id == project.id)).all()
        for _, child_total, child_active, child_archived in child_rows:
            total += int(child_total)
            active += int(child_active)
            archived += int(child_archived)
        return _to_view(project, total, active, archived, len(child_rows))

    def get_by_id(self, project_id: int) -> ProjectView | None:
        return self._get_one(Project.id == project_id)

    def get_by_public_id(self, public_id: str) -> ProjectView | None:
        return self._get_one(Project.public_id == public_id)

    def count_all(self) -> tuple[int, int]:
        """Return (total_project, project_aktif) dalam satu query."""
        row = db.session.execute(
            select(func.count(Project.id), func.sum(case((Project.archived.is_(False), 1), else_=0)))
        ).one()
        return row[0] or 0, int(row[1] or 0)

    def count_roots(self) -> tuple[int, int]:
        """Return (total_root, root_aktif) — statistik dashboard tanpa sub project."""
        row = db.session.execute(
            select(
                func.count(Project.id),
                func.coalesce(func.sum(case((Project.archived.is_(False), 1), else_=0)), 0),
            ).where(Project.parent_id.is_(None))
        ).one()
        return row[0] or 0, int(row[1] or 0)

    # ── Validasi (multi-layer: border form + sini — 16-security.md #4) ──
    def _validate(self, name: str, color: str) -> None:
        if not name or not name.strip():
            raise ValueError("Nama project wajib diisi.")
        if len(name.strip()) > 255:
            raise ValueError("Nama project maksimal 255 karakter.")
        if not HEX_COLOR_PATTERN.match(color or ""):
            raise ValueError("Warna harus format hex, mis. #3B82F6.")

    def _resolve_parent(self, parent_id, exclude_id: int | None = None) -> int | None:
        """Validasi parent: harus root, bukan diri sendiri. Kedalaman maks. 1 level."""
        if parent_id in (None, ""):
            return None
        try:
            pid = int(parent_id)
        except (TypeError, ValueError):
            raise ValueError("Parent project tidak valid.") from None
        if pid == exclude_id:
            raise ValueError("Project tidak bisa menjadi parent dirinya sendiri.")
        parent = db.session.get(Project, pid)
        if parent is None:
            raise ValueError("Parent project tidak ditemukan.")
        if parent.parent_id is not None:
            raise ValueError("Sub project tidak bisa memiliki sub project lagi (maksimal 2 level).")
        return pid

    def _has_children(self, project_id: int) -> bool:
        return db.session.scalar(
            select(Project.id).where(Project.parent_id == project_id).limit(1)
        ) is not None

    # ── Write ──
    def create(
        self,
        name: str,
        color: str,
        icon: str | None = None,
        parent_id=None,
    ) -> Project:
        self._validate(name, color)
        project = Project(
            name=name.strip(),
            color=color,
            icon=(icon or "").strip().removeprefix("fa-") or None,
            parent_id=self._resolve_parent(parent_id),
        )
        db.session.add(project)
        db.session.commit()
        return project

    def update(
        self,
        project_id: int,
        name: str,
        color: str,
        icon: str | None = None,
        parent_id=None,
    ) -> Project:
        project = db.session.get(Project, project_id)
        if project is None:
            raise ValueError("Project tidak ditemukan.")
        self._validate(name, color)
        resolved = self._resolve_parent(parent_id, exclude_id=project.id)
        if resolved is not None and self._has_children(project.id):
            raise ValueError(
                "Project ini memiliki sub project sehingga tidak bisa dijadikan sub project."
            )
        project.name = name.strip()
        project.color = color
        project.icon = (icon or "").strip().removeprefix("fa-") or None
        project.parent_id = resolved
        db.session.commit()
        return project

    def set_archived(self, project_id: int, archived: bool) -> Project:
        project = db.session.get(Project, project_id)
        if project is None:
            raise ValueError("Project tidak ditemukan.")
        project.archived = bool(archived)
        db.session.commit()
        return project

    def delete(self, project_id: int) -> Project:
        """Hapus project + sub project-nya; task di dalamnya dilepas (project_id = NULL)."""
        project = db.session.get(Project, project_id)
        if project is None:
            raise ValueError("Project tidak ditemukan.")
        child_ids = list(db.session.scalars(select(Project.id).where(Project.parent_id == project_id)))
        db.session.execute(
            update(Task).where(Task.project_id.in_([project_id, *child_ids])).values(project_id=None)
        )
        db.session.execute(delete(Project).where(Project.parent_id == project_id))
        db.session.delete(project)
        db.session.commit()
        return project


project_service = ProjectService()
