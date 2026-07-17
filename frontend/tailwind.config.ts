import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // ProblemForge design system — sleek dark slate + confident amber
        base: "#0F1115",
        surface: "#171A21",
        raised: "#1E2330",
        edge: "#262B36",
        ink: "#E7EBF3",
        muted: "#8A93A6",
        accent: {
          DEFAULT: "#F2A93B",
          hover: "#E09A28",
          soft: "#F2A93B1A",
        },
        teal: {
          DEFAULT: "#2DD4BF",
          soft: "#2DD4BF14",
        },
      },
      fontFamily: {
        sans: ["var(--font-inter)", "system-ui", "sans-serif"],
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
      borderRadius: {
        card: "12px",
      },
    },
  },
  plugins: [],
};

export default config;
