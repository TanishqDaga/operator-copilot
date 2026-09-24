/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      // Caterpillar machine-monitor theme (light): CAT yellow + CAT black on a warm light base.
      colors: {
        bg: '#F2EFE7',
        panel: '#FFFFFF',
        panel2: '#FAF8F3',
        raised: '#F2EDE2',
        line: '#E6E0D2',
        line2: '#D5CCB8',
        ink: '#1A1814',
        ink2: '#4A453C',
        ink3: '#6F6858',
        cat: { DEFAULT: '#FFCD11', dim: '#E5B800', ink: '#1A1400', black: '#1A1814' },
        safe: { DEFAULT: '#1E8A4C', bg: '#E4F4EA' },
        warn: { DEFAULT: '#C95F00', bg: '#FFF0DE' },
        crit: { DEFAULT: '#D32F2F', bg: '#FDE7E7' },
        info: { DEFAULT: '#1F6FC5', bg: '#E6F0FB' },
        anom: { DEFAULT: '#7A4FD6', bg: '#F0EAFD' },
      },
      // CAT yellow is a fill colour; as text on a light background it becomes a readable dark gold.
      textColor: {
        cat: { DEFAULT: '#8A6500', dim: '#6E5000', ink: '#1A1400', black: '#1A1814' },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'Segoe UI', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'Consolas', 'monospace'],
      },
      fontSize: {
        '2xs': ['11px', '14px'],
      },
      boxShadow: {
        card: '0 1px 2px 0 rgba(26,20,0,0.06), 0 8px 20px -14px rgba(26,20,0,0.25)',
      },
      keyframes: {
        pulseRing: { '0%': { boxShadow: '0 0 0 0 rgba(255,77,79,0.55)' }, '100%': { boxShadow: '0 0 0 18px rgba(255,77,79,0)' } },
        fadeUp: { '0%': { opacity: 0, transform: 'translateY(6px)' }, '100%': { opacity: 1, transform: 'none' } },
        rise: { '0%': { transform: 'translateY(8px) scale(0.98)' }, '100%': { transform: 'none' } },
        slideIn: { '0%': { opacity: 0, transform: 'translateX(24px)' }, '100%': { opacity: 1, transform: 'none' } },
        flash: { '0%': { backgroundColor: 'rgba(255,205,17,0.18)' }, '100%': { backgroundColor: 'transparent' } },
        critGlow: { '0%,100%': { opacity: 0.55 }, '50%': { opacity: 1 } },
      },
      animation: {
        pulseRing: 'pulseRing 1.2s ease-out infinite',
        fadeUp: 'fadeUp .35s cubic-bezier(.2,.7,.2,1) both',
        rise: 'rise .35s cubic-bezier(.2,.7,.2,1)',
        slideIn: 'slideIn .3s cubic-bezier(.2,.7,.2,1) both',
        flash: 'flash 1.2s ease-out',
        critGlow: 'critGlow 1.4s ease-in-out infinite',
      },
    },
  },
  plugins: [],
}
