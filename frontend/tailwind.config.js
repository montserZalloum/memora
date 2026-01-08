export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      fontFamily: { tajawal: ['Tajawal', 'sans-serif'] },
      colors: {
        primary: {
          DEFAULT: '#007D5B',
          dark: '#005A42',
          light: '#00A878',
          10: 'rgba(0, 125, 91, 0.1)'
        },
        secondary: {
          DEFAULT: '#E8A838',
          light: '#FFD166'
        },
        accent: {
          DEFAULT: '#D64550'
        },
        surface: {
          cream: '#FDF8F3',
          warm: '#F5EDE6'
        },
        state: {
          success: '#00B894',
          error: '#E17055'
        }
      },
      boxShadow: {
        'button': '0 4px 0px rgba(0, 90, 66, 1)',
        'button-pressed': '0 0px 0px rgba(0, 90, 66, 1)',
      },
      animation: {
        'shake': 'shake 0.5s cubic-bezier(.36,.07,.19,.97) both',
        'bounce-subtle': 'bounce-subtle 1s ease-in-out infinite',
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
      keyframes: {
        'bounce-subtle': {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-8px)' },
        }
      }
    },
  },
  plugins: [],
}
