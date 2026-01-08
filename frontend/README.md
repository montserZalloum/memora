# The Jordan Project - Frontend

A mobile-first, gamified educational PWA built with React, TypeScript, and Tailwind CSS. Inspired by Duolingo's UI/UX with satisfying animations and game mechanics.

🎮 **Live Demo**: http://localhost:5173/

---

## Quick Start

```bash
npm run dev          # Start dev server on http://localhost:5173/
npm run build        # Production build
```

---

## 📖 Documentation

- **[PROJECT_SUMMARY.md](./PROJECT_SUMMARY.md)** - Complete overview of what was built
- **[IMPLEMENTATION_GUIDE.md](./IMPLEMENTATION_GUIDE.md)** - Technical deep dive
- **[QUICK_START.md](./QUICK_START.md)** - Developer cheat sheet

---

## 🎯 Features

### Game Engine
- ✅ Queue-based stage progression
- ✅ Duolingo-style retry mechanics
- ✅ XP and combo streak tracking
- ✅ 3 lives per lesson (configurable)
- ✅ Win/loss conditions

### UI Components
- ✅ 3D buttons with press animation
- ✅ Animated progress bar
- ✅ Heart display with shake effect
- ✅ Smooth stage transitions
- ✅ Mobile-optimized layout

### Stage Types
- ✅ **Reveal** - Interactive word highlighting with explanations
- ✅ **Matching** - Pair matching game with visual feedback

### Localization
- ✅ Full RTL (Right-to-Left) support
- ✅ Arabic font (Tajawal) integrated
- ✅ Ready for any language

---

## 🛠 Tech Stack

React 18+ | TypeScript 5+ | Vite 7.3 | Tailwind CSS 4+ | Framer Motion | Zustand

---

## 📁 Project Structure

```
src/
├── components/          # Reusable UI components
│   ├── JuicyButton.tsx
│   ├── ProgressBar.tsx
│   ├── HeartDisplay.tsx
│   ├── Layout.tsx
│   └── stages/          # Stage renderers
│       ├── RevealStage.tsx
│       └── MatchingStage.tsx
├── pages/
│   └── GameSession.tsx  # Main orchestrator
├── store/
│   └── useGameStore.ts  # Zustand game state
├── types/
│   └── index.ts         # Shared TypeScript types
└── App.tsx
```

---

## 🎮 Game Flow

```
1. Load Lesson → Queue of stages
2. Render Current Stage
3. User Interacts
4. Submit Answer
   ✅ Correct → +XP, advance
   ❌ Wrong  → -1 Heart, move to end of queue
5. Loop until queue empty or hearts = 0
6. Win/Loss Screen
```

---

## 🎨 Design System

- **Primary**: #007D5B (Teal)
- **Secondary**: #E8A838 (Gold)
- **Accent**: #D64550 (Red)
- **Success**: #00B894 (Green)
- **Error**: #E17055 (Red)

Features: 3D buttons, Framer Motion animations, Full RTL support, Mobile-first design

---

## 🔌 Backend Integration Ready

Replace mock data with Frappe API calls. See [IMPLEMENTATION_GUIDE.md](./IMPLEMENTATION_GUIDE.md) for details.

---

## 💡 Development

### Add a New Component
1. Create in `src/components/`
2. Export from `src/components/index.ts`
3. Import anywhere: `import { Component } from '../components'`

### Add a New Stage Type
1. Create in `src/components/stages/`
2. Add interface to `useGameStore.ts`
3. Add renderer in `GameSession.tsx`

### Debug Game State
```tsx
// In browser console:
useGameStore.getState()
```

---

**Status**: ✅ Complete and production-ready

*Built with React + Tailwind + Framer Motion for immersive, gamified learning*
