"""tests/test_project_hierarchy.py — TC hierarki 2 level (Fase 3/4).

Cakupan: validasi kedalaman, pindah root/sub, hapus berantai, arsip cabang,
filter task subtree, dan route/UI sub project.
"""
import pytest

from app.extensions import db
from app.forms.task_forms import project_choices
from app.models import Project, Task
from app.services.project_service import project_service
from app.services.task_service import task_service


@pytest.fixture
def root(app):
    return project_service.create(name="Kuliah", color="#3B82F6")


@pytest.fixture
def sub(root):
    return project_service.create(name="Matkul A", color="#8B5CF6", parent_id=root.id)


class TestProjectHierarchyWrite:
    def test_create_sub_project(self, root, sub):
        assert sub.parent_id == root.id
        assert [p.id for p in project_service.get_roots()] == [root.id]
        assert [p.id for p in project_service.get_children(root.id)] == [sub.id]
        assert project_service.get_by_id(sub.id).parent_name == "Kuliah"

    def test_create_sub_dari_sub_ditolak(self, root, sub):
        with pytest.raises(ValueError, match="maksimal 2 level"):
            project_service.create(name="Cucu", color="#111111", parent_id=sub.id)

    def test_create_parent_tidak_ada(self, app):
        with pytest.raises(ValueError, match="tidak ditemukan"):
            project_service.create(name="X", color="#111111", parent_id=999)

    def test_update_sub_jadi_root(self, root, sub):
        project_service.update(sub.id, name="Matkul A", color="#8B5CF6", parent_id="")
        assert project_service.get_by_id(sub.id).parent_id is None

    def test_update_root_tanpa_child_jadi_sub(self, root):
        other = project_service.create(name="Kerja", color="#111111")
        project_service.update(root.id, name="Kuliah", color="#3B82F6", parent_id=str(other.id))
        assert project_service.get_by_id(root.id).parent_id == other.id

    def test_update_root_berchild_tidak_bisa_jadi_sub(self, root, sub):
        other = project_service.create(name="Kerja", color="#111111")
        with pytest.raises(ValueError, match="memiliki sub project"):
            project_service.update(root.id, name="Kuliah", color="#3B82F6", parent_id=str(other.id))

    def test_update_parent_diri_sendiri_ditolak(self, root):
        with pytest.raises(ValueError, match="dirinya sendiri"):
            project_service.update(root.id, name="Kuliah", color="#3B82F6", parent_id=str(root.id))

    def test_delete_root_menghapus_child_dan_melepas_task(self, root, sub):
        task_root = task_service.create(title="Tugas root", project_id=root.id)
        task_sub = task_service.create(title="Tugas sub", project_id=sub.id)
        root_id, sub_id, task_root_id, task_sub_id = root.id, sub.id, task_root.id, task_sub.id

        project_service.delete(root_id)
        db.session.expunge_all()

        assert db.session.get(Project, root_id) is None
        assert db.session.get(Project, sub_id) is None
        surviving = db.session.get(Task, task_root_id)
        assert surviving is not None and surviving.project_id is None
        assert db.session.get(Task, task_sub_id).project_id is None

    def test_archive_root_menyembunyikan_cabang(self, root, sub):
        project_service.set_archived(root.id, True)

        assert project_service.get_all() == []
        assert project_service.get_hierarchical() == []
        assert [c[0] for c in project_choices()] == [""]  # hanya opsi Inbox
        # data child tidak ikut diarsipkan — pulihkan root mengembalikan cabang
        assert project_service.get_by_id(sub.id).archived is False
        project_service.set_archived(root.id, False)
        assert [p.id for p in project_service.get_all()] == [root.id, sub.id] or {
            p.id for p in project_service.get_all()
        } == {root.id, sub.id}

    def test_count_roots_tanpa_sub(self, root, sub):
        other = project_service.create(name="Kerja", color="#111111")
        project_service.set_archived(other.id, True)
        assert project_service.count_roots() == (2, 1)
        assert project_service.count_all()[0] == 3


class TestTaskFilterSubtree:
    def test_task_root_mencakup_sub(self, root, sub):
        task_root = task_service.create(title="Root", project_id=root.id)
        task_sub = task_service.create(title="Sub", project_id=sub.id)
        task_other = task_service.create(title="Lain", project_id=None)

        ids = {t.id for t in task_service.get_all(filters={"project_id": root.id})}
        assert ids == {task_root.id, task_sub.id}
        assert task_other.id not in ids

    def test_arsip_root_mencakup_sub(self, root, sub):
        done = task_service.create(title="Selesai sub", project_id=sub.id, status="done")
        task_service.archive(done.id)
        archived = task_service.get_archived(filters={"project_id": root.id})
        assert [t.id for t in archived] == [done.id]

    def test_arsip_paginated_root_mencakup_sub(self, root, sub):
        done = task_service.create(title="Selesai sub", project_id=sub.id, status="done")
        task_service.archive(done.id)
        pagination = task_service.get_archived_paginated(filters={"project_id": root.id})
        assert [t.id for t in pagination.items] == [done.id]


class TestProjectHierarchyRoutes:
    def test_halaman_create_sub(self, client, login_user, root):
        response = client.get(f"/projects/{root.public_id}/sub/create")
        assert response.status_code == 200
        assert b"Tambah Sub Project" in response.data
        assert b"Kuliah" in response.data

    def test_post_create_sub(self, client, login_user, root):
        response = client.post(
            f"/projects/{root.public_id}/sub/create",
            data={"name": "Matkul B", "color": "#10B981", "icon": "book"},
            follow_redirects=False,
        )
        assert response.status_code == 302
        child = db.session.query(Project).filter_by(name="Matkul B").first()
        assert child is not None
        assert child.parent_id == root.id

    def test_create_sub_dari_sub_ditolak(self, client, login_user, root, sub):
        response = client.post(
            f"/projects/{sub.public_id}/sub/create",
            data={"name": "Cucu", "color": "#10B981", "icon": ""},
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"maksimal 2 level" in response.data
        assert db.session.query(Project).filter_by(name="Cucu").first() is None

    def test_create_sub_di_project_arsip_ditolak(self, client, login_user, root):
        project_service.set_archived(root.id, True)
        response = client.post(
            f"/projects/{root.public_id}/sub/create",
            data={"name": "Anak Arsip", "color": "#10B981", "icon": ""},
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"diarsipkan" in response.data
        assert db.session.query(Project).filter_by(name="Anak Arsip").first() is None

    def test_edit_pindahkan_sub_ke_root(self, client, login_user, root, sub):
        response = client.post(
            f"/projects/{sub.public_id}/edit",
            data={"name": "Matkul A", "color": "#8B5CF6", "icon": "", "parent_id": ""},
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert project_service.get_by_id(sub.id).parent_id is None

    def test_edit_halaman_tampilkan_parent(self, client, login_user, sub):
        response = client.get(f"/projects/{sub.public_id}/edit")
        assert response.status_code == 200
        assert b"Parent Project" in response.data

    def test_edit_root_berchild_tanpa_parent_tetap_root(self, client, login_user, root, sub):
        """Field parent disembunyikan untuk root berchild — submit tanpa parent_id tetap root."""
        response = client.post(
            f"/projects/{root.public_id}/edit",
            data={"name": "Kuliah", "color": "#3B82F6", "icon": ""},
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert project_service.get_by_id(root.id).parent_id is None
        assert project_service.get_by_id(sub.id).parent_id == root.id

    def test_detail_root_tampilkan_sub_dan_task_subtree(self, client, login_user, root, sub):
        task_service.create(title="Tugas di sub", project_id=sub.id)

        response = client.get(f"/projects/{root.public_id}")
        assert response.status_code == 200
        assert b"Sub Project" in response.data
        assert b"Matkul A" in response.data
        assert b"Tugas di sub" in response.data
        assert b"Statistik dan daftar tugas menjumlahkan" in response.data

    def test_detail_sub_punya_breadcrumb_parent(self, client, login_user, root, sub):
        response = client.get(f"/projects/{sub.public_id}")
        assert response.status_code == 200
        assert b"Sub Project" in response.data
        assert b"bagian dari" in response.data

    def test_list_project_hanya_root(self, client, login_user, root, sub):
        response = client.get("/projects/")
        assert response.status_code == 200
        assert b"Kuliah" in response.data
        assert b"Matkul A" not in response.data

    def test_dashboard_hanya_root(self, client, login_user, root, sub):
        response = client.get("/")
        assert response.status_code == 200
        assert b"Kuliah" in response.data
        assert b"Matkul A" not in response.data
        assert b"1 sub project" in response.data

    def test_filter_task_route_mencakup_sub(self, client, login_user, root, sub):
        task_service.create(title="Tugas di sub", project_id=sub.id)
        response = client.get(f"/tasks/?project_id={root.id}")
        assert response.status_code == 200
        assert b"Tugas di sub" in response.data

    def test_task_create_preselect_sub_project(self, client, login_user, root, sub):
        """Link 'Tambah Tugas' dari detail mengirim public_id — harus terpilih."""
        response = client.get(f"/tasks/create?project_id={sub.public_id}")
        assert response.status_code == 200
        assert f'value="{sub.id}" selected'.encode() in response.data

    def test_delete_root_via_route(self, client, login_user, root, sub):
        task = task_service.create(title="T", project_id=sub.id)
        response = client.post(f"/projects/{root.public_id}/delete", follow_redirects=True)
        assert response.status_code == 200
        assert db.session.get(Project, sub.id) is None
        assert db.session.get(Task, task.id).project_id is None

    def test_archive_sub_redirect_ke_parent(self, client, login_user, root, sub):
        response = client.post(
            f"/projects/{sub.public_id}/archive",
            data={"archived": "true"},
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert response.headers["Location"].endswith(f"/projects/{root.public_id}")
        assert project_service.get_by_id(sub.id).archived is True

    def test_delete_sub_redirect_ke_parent(self, client, login_user, root, sub):
        response = client.post(f"/projects/{sub.public_id}/delete", follow_redirects=False)
        assert response.status_code == 302
        assert response.headers["Location"].endswith(f"/projects/{root.public_id}")
        assert db.session.get(Project, sub.id) is None
