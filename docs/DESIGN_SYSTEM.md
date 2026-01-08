# DESIGN_SYSTEM.md

> **System Name:** Juicy Jordan UI  
> **Platform:** Mobile-First Web App (PWA)  
> **Framework:** React + Tailwind CSS + Framer Motion  
> **Direction:** RTL (Arabic)

---

## 1. Design Philosophy
We are not building a "website"; we are building a **Game Interface**.
*   **Juicy:** Everything pops, bounces, and gives feedback.
*   **Tactile:** Buttons look clickable (3D effect), cards have depth.
*   **Warm:** Colors are earthy (Jordanian landscape) but vibrant.
*   **Round:** No sharp corners. Everything is `rounded-2xl` or `rounded-3xl`.

---

## 2. Tailwind Configuration (`tailwind.config.js`)

The AI Developer must use this exact configuration to match the prototype colors.

```javascript
/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        tajawal: ['Tajawal', 'sans-serif'],
      },
      colors: {
        primary: {
          DEFAULT: '#007D5B', // The Jordan Green
          dark: '#005A42',
          light: '#00A878',
          10: 'rgba(0, 125, 91, 0.1)', // For soft backgrounds
        },
        secondary: {
          DEFAULT: '#E8A838', // Golden Desert
          light: '#FFD166',
        },
        accent: {
          DEFAULT: '#D64550', // Jordan Red
          hover: '#C0392B',
        },
        surface: {
          cream: '#FDF8F3', // Main background
          warm: '#F5EDE6',  // Card background
        },
        text: {
          dark: '#2D3436',
          muted: '#636E72',
        },
        state: {
          success: '#00B894',
          error: '#E17055',
          info: '#3498DB',
        }
      },
      boxShadow: {
        'card': '0 4px 20px rgba(0, 125, 91, 0.15)',
        'hover': '0 8px 30px rgba(0, 125, 91, 0.25)',
        'button': '0 4px 0px rgba(0, 90, 66, 1)', // 3D Effect for buttons
        'button-pressed': '0 0px 0px rgba(0, 90, 66, 1)',
      },
      backgroundImage: {
        'pattern-overlay': "url(\"data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' ... \")", // Use the SVG from original HTML
        'gradient-main': 'linear-gradient(135deg, #007D5B 0%, #005A42 100%)',
        'gradient-gold': 'linear-gradient(135deg, #FFD166 0%, #E8A838 100%)',
      },
      animation: {
        'bounce-slow': 'bounce 3s infinite',
        'pop': 'pop 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275)',
        'shake': 'shake 0.5s cubic-bezier(.36,.07,.19,.97) both',
      },
      keyframes: {
        pop: {
          '0%': { transform: 'scale(0.8)', opacity: '0' },
          '50%': { transform: 'scale(1.1)' },
          '100%': { transform: 'scale(1)', opacity: '1' },
        },
        shake: {
          '10%, 90%': { transform: 'translate3d(-1px, 0, 0)' },
          '20%, 80%': { transform: 'translate3d(2px, 0, 0)' },
          '30%, 50%, 70%': { transform: 'translate3d(-4px, 0, 0)' },
          '40%, 60%': { transform: 'translate3d(4px, 0, 0)' }
        }
      }
    },
  },
  plugins: [],
}
```

---

## 3. Core Component Specs

### A. The "Juicy" Button (`<Button />`)
*   **Base:** `w-full py-4 rounded-full font-bold text-xl transition-all active:translate-y-[4px]`
*   **Primary Variant:** `bg-gradient-main text-white shadow-button active:shadow-button-pressed`
*   **Secondary Variant:** `bg-white border-2 border-gray-200 text-text-muted hover:bg-surface-warm`
*   **Disabled State:** `opacity-50 cursor-not-allowed shadow-none translate-y-[2px]`

### B. The Lesson Card (`<Card />`)
*   **Style:** `bg-white rounded-3xl p-6 shadow-card border-b-4 border-gray-100`
*   **Context:** Used for the main game container and dialogs.

### C. The Progress Bar
*   **Container:** `h-4 bg-surface-warm rounded-full overflow-hidden`
*   **Fill:** `h-full bg-gradient-to-r from-primary to-primary-light transition-all duration-500 ease-out`
*   **Glow:** Add a slight white shine on top (`absolute top-0 left-0 w-full h-1/2 bg-white/30`) for a glass effect.

---

## 4. Stage-Specific Layouts (The "Gameplay")

### Type 1: Reveal Stage (`game.reveal`)
*   **Layout:** Vertical Stack (Flex-Col).
*   **Hero Image:** A large card in the center (`w-48 h-48`) with the emoji/icon.
*   **Typography:** Large sentence (`text-2xl leading-loose text-center`).
*   **Interaction:**
    *   Words with a "Highlight" property must be wrapped in a span: `bg-secondary-light/30 px-2 rounded-lg cursor-pointer border-b-2 border-secondary`.
    *   **On Click:** Pop a small tooltip/modal with the explanation. Play sound.

### Type 2: Matching Stage (`game.matching`)
*   **Layout:** Two columns (`grid grid-cols-2 gap-4`).
*   **Items:**
    *   **Default:** `bg-white border-2 border-gray-200 rounded-xl p-4 text-center font-bold shadow-sm`
    *   **Selected:** `border-primary bg-primary-10 scale-105`
    *   **Matched:** `border-state-success bg-green-50 text-state-success opacity-50`
    *   **Error:** `border-state-error bg-red-50 animate-shake`

### Type 3: Story/Chat Stage (`game.story`)
*   **Layout:** Chat Interface (`flex flex-col gap-4 overflow-y-auto`).
*   **Bubbles:**
    *   **NPC (Grandfather):** `bg-surface-warm rounded-tl-none rounded-2xl p-4 self-start max-w-[80%]` (Icon on Left).
    *   **User (Hero):** `bg-primary text-white rounded-tr-none rounded-2xl p-4 self-end max-w-[80%]` (Icon on Right).
*   **Options:** Buttons appear at the bottom of the screen.

---

## 5. Animation Guidelines (Framer Motion)

Use `framer-motion` for all transitions.

1.  **Page Transition:**
    *   `initial={{ opacity: 0, x: 20 }}`
    *   `animate={{ opacity: 1, x: 0 }}`
    *   `exit={{ opacity: 0, x: -20 }}`
2.  **Success Feedback:**
    *   When an answer is correct, trigger a confetti explosion.
    *   Show a bottom sheet (Modal) sliding up: `y: "100%"` -> `y: 0`.
3.  **Hearts:**
    *   When a heart is lost, animate it shaking and turning grey.

---

## 6. Iconography
*   Use standard Emojis for the MVP (as in the HTML).
*   For UI icons (Back, Settings, Sound), use **Lucide React** (`lucide-react`).