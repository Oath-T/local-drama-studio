import type { Config } from "tailwindcss";
import tailwindcssAnimate from "tailwindcss-animate";

const config: Config = {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        background: "#111315",
        panel: "#181b1f",
        panelRaised: "#20242a",
        border: "#2b3037",
        muted: "#8a94a3",
        foreground: "#edf1f5",
        primary: "#5d83b8",
        primarySoft: "#27384d",
        success: "#4f9f73",
        danger: "#bd5c5c",
        studio: {
          page: "var(--studio-color-page)",
          workspace: "var(--studio-color-workspace)",
          panel: "var(--studio-color-panel)",
          surface: "var(--studio-color-surface)",
          hover: "var(--studio-color-hover)",
          selected: "var(--studio-color-selected)",
          border: "var(--studio-color-border)",
          foreground: "var(--studio-color-text)",
          muted: "var(--studio-color-text-muted)",
          primary: "var(--studio-color-primary)",
          success: "var(--studio-color-success)",
          warning: "var(--studio-color-warning)",
          danger: "var(--studio-color-danger)",
          info: "var(--studio-color-info)"
        }
      },
      boxShadow: {
        workbench: "0 1px 0 rgba(255,255,255,0.04) inset"
      }
    }
  },
  plugins: [tailwindcssAnimate]
};

export default config;
