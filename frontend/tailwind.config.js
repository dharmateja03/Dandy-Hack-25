export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Space Grotesk', 'ui-sans-serif', 'system-ui'],
        serif: ['var(--font-instrument-serif)', 'serif'],
        mono: ['Space Grotesk', 'ui-monospace', 'SFMono-Regular'],
      },
      colors: {
        midnight: "#0f0320",
        deeppurple: "#1a0b2e",
        mistgray: "#f3e8ff",
        glowpurple: "#a855f7",
        accentpurple: "#8b5cf6",
      },
    },
  },
  plugins: [],
}
