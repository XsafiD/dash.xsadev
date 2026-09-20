// Theme binding — token xsadev-kit (neutral-light) + token lama project.
// Salinan dari docs/xsadev-kit/core/themes/neutral-light.js, digabung dengan
// token project yang masih dipakai halaman terautentikasi agar tidak break.
// Ganti tampilan = ganti file ini, bukan sunting shell/komponen.
window.UI_KIT_THEME = {
  colors: {
    // ── Token kit ──
    canvas: "#F3F4F6",
    surface: { DEFAULT: "#FFFFFF", soft: "#F9FAFB" },
    "surface-elevated": "#EEF2F6",
    hairline: { DEFAULT: "#E5E7EB", soft: "#F3F4F6" },
    ink: { DEFAULT: "#1F2937", deep: "#111827" },
    "on-canvas": "#111827",
    muted: "#64748B",
    "muted-strong": "#475569",
    primary: { DEFAULT: "#2563EB", deep: "#1D4ED8", soft: "rgba(37, 99, 235, 0.10)" },
    "primary-active": "#1D4ED8",
    "primary-disabled": "#BFDBFE",
    "on-primary": "#FFFFFF",
    income: "#16A34A",
    expense: "#DC2626",
    success: { DEFAULT: "#16A34A", ink: "#15803D", soft: "rgba(22, 163, 74, 0.10)" },
    danger: "#DC2626",
    info: { DEFAULT: "#0EA5E9", ink: "#0369A1" },

    // ── Token lama project (dipertahankan) ──
    warning: { DEFAULT: "#F59E0B", ink: "#92400E", soft: "rgba(245, 158, 11, 0.10)" },
    critical: { DEFAULT: "#DC2626", ink: "#B91C1C" },
    charcoal: "#374151",
    slate: "#6B7280",
    steel: "#696F80",
    stone: "#646B7C",
  },
  borderRadius: { md: "6px", lg: "8px", xl: "12px" },
  fontFamily: {
    sans: ["Inter", "-apple-system", "BlinkMacSystemFont", "Segoe UI", "Roboto", "sans-serif"],
    numeric: ["'JetBrains Mono'", "ui-monospace", "SFMono-Regular", "monospace"],
  },
};
