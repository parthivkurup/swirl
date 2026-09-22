import type { Config } from "tailwindcss";

// The `ink` scale and `live` accent are the public dashboard's palette only.
// They are additive: /review and /submit keep Tailwind's default neutrals, and
// fontFamily.sans is deliberately not overridden so preflight leaves them alone.
const config: Config = {
  content: ["./app/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          bg: "#0A0A0B",
          line: "#212125",
          lineStrong: "#2E2E34",
          hi: "#F2F2F3",
          mid: "#A1A1A8",
          low: "#85858E",
        },
        live: "#43D9A3",
      },
      fontFamily: {
        froyo: ["var(--font-geist-sans)", "ui-sans-serif", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};
export default config;
