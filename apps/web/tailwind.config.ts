import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        bg: {
          DEFAULT: "#0a0d18",
          subtle: "#0f1322",
          raised: "#161b2d",
          overlay: "#1d2340",
        },
        border: {
          DEFAULT: "#262d48",
          muted: "#1c2238",
        },
        fg: {
          DEFAULT: "#e6e9f4",
          muted: "#9aa3c0",
          subtle: "#6b7390",
        },
        brand: {
          DEFAULT: "#8DECB4",
          strong: "#5dd99a",
          soft: "#8DECB420",
        },
        verdict: {
          supported: "#5dd99a",
          refuted: "#f87171",
          unverifiable: "#fbbf24",
        },
      },
      fontFamily: {
        sans: ["var(--font-sans)", "ui-sans-serif", "system-ui"],
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
      boxShadow: {
        glow: "0 0 0 1px #8DECB430, 0 8px 28px -12px #8DECB44d",
      },
      keyframes: {
        shimmer: {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
        "fade-in": {
          "0%": { opacity: "0", transform: "translateY(4px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
      animation: {
        shimmer: "shimmer 2s linear infinite",
        "fade-in": "fade-in 240ms ease-out",
      },
    },
  },
  plugins: [],
};

export default config;
