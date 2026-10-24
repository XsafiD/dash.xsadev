"""Form Project."""
from flask_wtf import FlaskForm
from wtforms import SelectField, StringField
from wtforms.validators import DataRequired, Length, Optional, Regexp

HEX_COLOR_PATTERN = r"^#[0-9A-Fa-f]{6}$"


class ProjectForm(FlaskForm):
    """Dipakai untuk create & edit — field sama, cukup satu form.

    `parent_id` hanya dirender di halaman edit (pindah root/sub). Halaman
    create root & create sub menyembunyikannya (parent ditentukan route).
    Pilihan parent di-set di controller karena butuh data service.
    """

    name = StringField("Nama Project", validators=[
        DataRequired(message="Nama project wajib diisi."),
        Length(min=1, max=255, message="Nama maksimal 255 karakter."),
    ])
    color = StringField("Warna", validators=[
        DataRequired(message="Warna wajib diisi."),
        Regexp(HEX_COLOR_PATTERN, message="Format warna harus hex, mis. #3B82F6."),
    ], default="#3B82F6")
    icon = StringField("Ikon (nama Font Awesome)", validators=[
        Optional(),
        Length(max=50, message="Nama ikon maksimal 50 karakter."),
    ], description="Tanpa prefix, mis. briefcase")
    parent_id = SelectField(
        "Parent Project",
        choices=[("", "— Jadikan Project Utama —")],
        coerce=str,
        validators=[Optional()],
    )
