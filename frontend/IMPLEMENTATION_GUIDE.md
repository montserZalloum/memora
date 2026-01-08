# Jordan Project - Frontend Implementation Guide

## 🎮 Project Overview

The Jordan Project is a **Mobile-First, Gamified Educational PWA** built with React, TypeScript, and Tailwind CSS. It provides an immersive learning experience with animations, sound, and progression tracking inspired by Duolingo.

**Dev Server**: http://localhost:5173/

---

## 📋 Project Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── JuicyButton.tsx         # 3D button with press animation
│   │   ├── ProgressBar.tsx         # Animated lesson progress indicator
│   │   ├── HeartDisplay.tsx        # Live count with shake effect
│   │   ├── Layout.tsx              # RTL mobile container wrapper
│   │   ├── stages/
│   │   │   ├── RevealStage.tsx     # Interactive word highlighting
│   │   │   └── MatchingStage.tsx   # Pair matching game
│   │   └── index.ts                # Barrel export
│   ├── pages/
│   │   └── GameSession.tsx         # Main orchestrator component
│   ├── store/
│   │   └── useGameStore.ts         # Zustand game state & logic
│   ├── App.tsx                     # Root component
│   ├── main.tsx                    # Entry point
│   └── index.css                   # Global styles + Tailwind
├── vite.config.ts
├── tailwind.config.js              # Custom color theme
├── postcss.config.js
├── tsconfig.json
└── package.json
```

---

## 🎨 Design System ("Juicy Jordan UI")

### Color Palette
```js
primary: {
  DEFAULT: '#007D5B',      // Teal (main accent)
  dark: '#005A42',         // Dark teal (shadows)
  light: '#00A878',        // Light teal
  10: 'rgba(0, 125, 91, 0.1)' // 10% opacity
}
secondary: {
  DEFAULT: '#E8A838',      // Gold (combo/fire)
  light: '#FFD166'         // Light gold
}
accent: {
  DEFAULT: '#D64550'       // Red (hearts/mistakes)
}
surface: {
  cream: '#FDF8F3',        // Background
  warm: '#F5EDE6'          // Card backgrounds
}
state: {
  success: '#00B894',      // Green (correct)
  error: '#E17055'         // Red (wrong)
}
```

### Key Features
- **3D Button Effect**: Uses `box-shadow` for depth, with Y-axis translation on press
- **RTL Support**: Full right-to-left text direction and layout
- **Mobile-First**: Max-width 480px, full viewport height (`h-dvh`)
- **Animations**: Framer Motion for smooth, satisfying interactions
- **Tailwind CSS**: Utility-first styling with custom theme

---

## 🧠 Core Logic: Zustand Game Store

The `useGameStore` implements Duolingo-style retry mechanics:

### Key Concepts

1. **Queue System**
   - `stageQueue`: All stages to complete in order
   - `retryQueue`: Tracks failed stages (moved to end of queue)
   - `currentStageIndex`: Current position in queue

2. **Duolingo Retry Mechanic**
   ```
   ✅ Correct Answer → Remove from queue, +XP, +combo
   ❌ Wrong Answer → Move to end of queue, -1 heart, combo=0
   ```

3. **Win/Loss Conditions**
   - **Win**: `stageQueue.length === 0` (all stages complete)
   - **Loss**: `hearts === 0` (no lives remaining)

### Store Interface

```ts
// Actions
loadLesson(stages: GameStage[])        // Initialize lesson
submitAnswer(isCorrect: boolean)       // Process answer (main logic)
resetGame()                            // Clear all state
addXP(amount: number)                  // Bonus XP
loseHeart()                            // Lose a life
nextStage()                            // Manual progression

// State
stageQueue: GameStage[]
currentStageIndex: number
currentXP: number
comboStreak: number
hearts: number
isGameActive: boolean
isGameWon: boolean
isGameOver: boolean
```

---

## 🎯 Stage Types

### 1. **Reveal Stage** (`RevealStage.tsx`)
Interactive word highlighting with bottom-sheet explanations.

**Config Format**:
```ts
{
  image: '📚',                    // Emoji or image URL
  sentence: 'هذا كتاب جديد',      // Arabic text
  highlights: [
    {
      word: 'كتاب',
      explanation: 'A written work containing knowledge'
    }
  ]
}
```

**User Interaction**:
1. User clicks highlighted words
2. Bottom sheet slides up with explanation
3. Complete button changes to "✓ فهمت" when all words revealed
4. Tapping complete marks stage as correct

---

### 2. **Matching Stage** (`MatchingStage.tsx`)
Connect pairs from left column to right column.

**Config Format**:
```ts
{
  instruction: 'طابق الكلمات مع معانيها',
  pairs: [
    { id: '1', left: 'ماء', right: 'سائل شفاف' },
    { id: '2', left: 'نار', right: 'حرارة وضوء' }
  ]
}
```

**User Interaction**:
1. Click left item to select
2. Click right item to match
3. Correct matches stay highlighted in green
4. Wrong matches shake red briefly
5. Auto-complete when all pairs matched

---

## 📱 UI Components

### JuicyButton
```tsx
<JuicyButton
  onClick={() => {}}
  variant="primary"      // 'primary' | 'secondary' | 'accent' | 'success' | 'error'
  size="lg"              // 'sm' | 'md' | 'lg'
  fullWidth
>
  Click Me
</JuicyButton>
```

**Features**:
- Framer Motion scale/tap animations
- 3D shadow effect on hover
- Press animation with shadow compression
- Accessibility focus states

### ProgressBar
```tsx
<ProgressBar
  current={3}
  total={10}
  variant="primary"     // 'primary' | 'secondary' | 'success'
/>
```

### HeartDisplay
```tsx
<HeartDisplay
  current={3}
  max={3}
  isShaking={wasWrong}  // Triggers shake animation
/>
```

---

## 🔌 Integration: Connecting to Frappe Backend

The backend is already set up in `/home/corex/aurevia-bench/apps/memora/memora/` with:
- `Game Lesson` DocType
- `Game Stage` DocType with content builders
- `game_lesson.js` for Frappe UI integrations

### API Integration Steps

1. **Replace Mock Data** in `GameSession.tsx`:
   ```tsx
   useEffect(() => {
     // Replace with API call:
     const fetchLesson = async () => {
       const res = await fetch(`/api/resource/Game Lesson/${lessonId}`);
       const lesson = await res.json();
       loadLesson(lesson.stages);
     };
   }, []);
   ```

2. **Submit Progress**:
   ```tsx
   const handleStageComplete = async (isCorrect: boolean) => {
     submitAnswer(isCorrect);

     // Post to Frappe
     await fetch('/api/resource/Game Progress', {
       method: 'POST',
       body: JSON.stringify({
         user: frappe.session.user,
         lesson_id: lessonId,
         stage_id: currentStage.id,
         is_correct: isCorrect,
         xp_earned: currentXP
       })
     });
   };
   ```

---

## 🚀 Running the Project

### Development
```bash
cd /home/corex/aurevia-bench/apps/memora/frontend
npm run dev
# Runs on http://localhost:5173/
```

### Production Build
```bash
npm run build
# Output in dist/
```

### Type Checking
```bash
npm run build  # tsc -b runs first
```

---

## 📦 Dependencies

| Package | Purpose |
|---------|---------|
| `react` | UI framework |
| `framer-motion` | Animations (juicy feel) |
| `zustand` | State management |
| `lucide-react` | Icon library |
| `tailwindcss` | Styling |
| `use-sound` | Audio effects (optional) |
| `clsx` | Conditional classNames |

---

## 🎬 Next Steps

### Phase 1: Backend Integration
- [ ] Connect to Frappe API for lesson loading
- [ ] Post progress/XP to backend
- [ ] Load user profile data

### Phase 2: New Stage Types
- [ ] `Quiz` - Multiple choice questions
- [ ] `Story` - Narrative-based learning
- [ ] `Audio` - Pronunciation training

### Phase 3: Polish
- [ ] Add sound effects (use `use-sound`)
- [ ] Add haptic feedback (vibration on mobile)
- [ ] Offline support (service workers)
- [ ] Push notifications for streaks

### Phase 4: Analytics
- [ ] Track lesson completion rates
- [ ] Time-to-complete metrics
- [ ] Difficulty assessment

---

## 💡 Key Architecture Decisions

1. **Zustand over Redux**: Lightweight, minimal boilerplate, perfect for game state
2. **Framer Motion**: CSS animations lack satisfying spring physics
3. **Tailwind**: Rapid prototyping, consistent design tokens
4. **Component Composition**: Each stage type is independent, easy to extend
5. **RTL-First**: Direction baked into design, not an afterthought

---

## 🎯 Performance Tips

1. **Lazy Loading**: Import stage components on demand
   ```tsx
   const RevealStage = lazy(() => import('./stages/RevealStage'));
   ```

2. **Memoization**: Stages don't change during gameplay
   ```tsx
   const GameSession = memo(({ lessonId }) => ...);
   ```

3. **Image Optimization**: Use emoji or SVG, minimize HTTP requests

4. **Code Splitting**: Vite automatically chunks dependencies

---

## 🛠 Debugging

Enable Zustand devtools in development:
```tsx
// Add to store config
// { name: 'GameStore', store: useGameStore }
```

Monitor Framer Motion animations:
```tsx
<motion.div animate={{ ... }} initial={{ ... }}>
  {/* Add debugger: true to motion config */}
</motion.div>
```

---

## 📞 Support

For issues:
1. Check TypeScript errors: `npm run build`
2. Inspect Zustand state in React DevTools
3. Review Vite HMR errors in browser console
4. Check Tailwind class generation in `dist/`

---

**Status**: ✅ All components built and tested. Ready for backend integration!
