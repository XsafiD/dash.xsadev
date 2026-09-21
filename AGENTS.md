# AGENTS.md Snippet — Flask Coding Standards

---

## Coding Standards (WAJIB)

Standards repo ini: `docs/coding-standards/` (git submodule).

**Aturan konsumsi:**

1. Sebelum menulis/mengubah kode, baca `docs/coding-standards/coding-rules/_INDEX.md`
2. Load HANYA rule file yang relevan dengan topik yang dikerjakan (mis. ubah model → `02-model.md`) — jangan baca semua
3. Istilah di rules pakai archetype (`Actor`, `Entity`, `Transaction`) — map ke domain project ini saat apply. Bila bingung mapping, baca `_GLOSSARY.md`
4. Deep-dive `../reference/` hanya bila rule file dirasa kurang jelas — opsional, bukan default
5. `DEFAULT COPY-PASTE` section di tiap rule = starting point snippet, sesuaikan naming domain

**Mapping archetype project ini** (isi saat project dimulai):

| Archetype   | Domain project ini |
| ----------- | ------------------ |
| Actor       | User (tabel `users`, single-user; fitur multi-user menyusul) |
| AdminRole   | — (belum ada, single-user) |
| Entity      | Project |
| Transaction | Task |
| TransactionLine | Reminder (disabled — fase notifikasi) |

---

## UI Kit (WAJIB)

UI kit: `docs/xsadev-kit/` (git submodule → `XsafiD/xsadev-kit`, pin `v1.1.0`).
Snippet lengkap: `docs/xsadev-kit/AGENTS-snippet.md`.

**Aturan konsumsi:**

1. Kontrak token: `docs/xsadev-kit/core/TOKENS.md`
2. Kontrak markup + `data-*` & API komponen: `docs/xsadev-kit/core/patterns/`
3. Panduan generik: `docs/xsadev-kit/guides/`
4. Adapter Flask: `docs/xsadev-kit/adapters/flask/` — aset **disalin** ke `app/templates/` + `app/static/`, jangan import dari submodule saat runtime
5. Ganti tampilan = ganti `app/static/js/theme.js`, bukan sunting shell/komponen
6. "Kenapa" visual project: `DESIGN.md`

**WAJIB:**

1. Pakai komponen kit; jangan menulis `<select>` polos / menggambar ulang dropdown per halaman.
2. Jaga fallback native (`<select>` asli) — form tetap jalan tanpa JS.
3. **Class dasar kontrol dari SATU sumber.** Definisi class dasar input (padding, rounded, border, focus) ada di `app/templates/components/form.html` (`field_class`) dan **di-import** oleh `components/dropdown.html` — jangan menyalin string class ke komponen lain.
4. Semua kontrol form seragam tinggi, padding, radius, dan tipografinya (`py-2.5`, `rounded-lg`, `text-[14px]`).
5. Jangan mengubah token/nama `data-*` ad-hoc; selaraskan lewat kit.

**DILARANG:**

| Anti-pattern | Konsekuensi |
|---|---|
| Menyalin string class antar komponen | Drift ukuran (mis. dropdown lebih pendek karena `py-*` tertinggal) |
| Bikin dropdown/segmented sendiri per halaman | Tampilan beda + JS ganda tak terawat |
| Menghapus fallback native | Rusak tanpa JS, aksesibilitas turun |
| Hardcode warna state aktif | Token bocor; ganti tema harus sunting halaman |

---
