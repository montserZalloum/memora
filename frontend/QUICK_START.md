# Jordan Project - Quick Start Guide

## 🚀 Quick Setup

```bash
# Already installed! Just start the dev server:
cd /home/corex/aurevia-bench/apps/memora/frontend
npm run dev
```

**→ Open http://localhost:5173/ in your browser**

---

## 📖 File Navigation Guide

### Add a New Stage Type

1. **Create the component** in `src/components/stages/NewStage.tsx`:
```tsx
import type { GameStage, NewConfig } from '../../store/useGameStore';

export const NewStage: React.FC<{ stage: GameStage; onComplete: (isCorrect: boolean) => void }> = ({
  stage,
  onComplete,
}) => {
  // Your UI here
  return (
    <div>
      <JuicyButton onClick={() => onComplete(true)}>Submit</JuicyButton>
    </div>
  );
};
```

2. **Add type to store** in `src/store/useGameStore.ts`:
```ts
export type StageType = 'Reveal' | 'Matching' | 'Quiz' | 'NewStage';

export interface NewConfig {
  // Your config shape
}
```

3. **Add renderer** in `src/pages/GameSession.tsx`:
```tsx
case 'NewStage':
  return <NewStage stage={currentStage} onComplete={handleStageComplete} />;
```

### Add a New UI Component

1. **Create in** `src/components/NewComponent.tsx`
2. **Export from** `src/components/index.ts`
3. **Import anywhere**: `import { NewComponent } from '../components'`

---

## 🎮 Game Flow Diagram

```
GameSession.tsx (Main Orchestrator)
    ├── Load Lesson → store.loadLesson()
    ├── Render Current Stage
    │   ├── RevealStage / MatchingStage / etc.
    │   └── User Interaction
    │
    ├── onComplete(isCorrect)
    │   └── store.submitAnswer(isCorrect)
    │       ├── ✅ Correct → Remove from queue, +XP, move forward
    │       └── ❌ Wrong → Move to end of queue, -1 heart
    │
    ├── Loop until stageQueue is empty
    └── Win/Loss Screen
```

---

## 🎨 Styling Quick Reference

### Tailwind Classes Used
- `bg-primary` / `bg-secondary` / `bg-accent` - Colors
- `text-white` / `text-gray-600` - Text colors
- `p-4` / `px-6` / `py-3` - Padding
- `rounded-lg` / `rounded-full` - Border radius
- `shadow-button` - 3D button effect
- `flex` / `flex-col` / `gap-4` - Layout
- `animate-shake` - Shake animation
- `h-dvh` - Full viewport height

### Add Custom Colors
Edit `tailwind.config.js`:
```js
colors: {
  myColor: '#123456'
}
```

Then use: `bg-myColor`

---

## 🧪 Testing the Game Flow

### Test Scenario 1: Win Game
1. Start at Reveal stage
2. Click all highlighted words
3. Click "فهمت" button
4. Moves to Matching stage
5. Match all pairs correctly
6. Win screen appears

### Test Scenario 2: Lose Game
1. Start at Matching stage
2. Make 3 wrong matches
3. Hearts go to 0
4. Game Over screen appears

### Test Scenario 3: Retry Logic
1. Match 1 pair correctly
2. Make 1 wrong match → moved to end of queue
3. Continue until all matched
4. Should show progress: "2/3" then "3/3"

---

## 🔧 Common Tasks

### Change Lesson Data
Edit `GameSession.tsx`:
```tsx
useEffect(() => {
  const mockLesson: GameStage[] = [
    // Add your stages here
  ];
  loadLesson(mockLesson);
}, []);
```

### Change Button Colors
```tsx
<JuicyButton variant="secondary">  // Try: primary, secondary, accent, success, error
  Click me
</JuicyButton>
```

### Add More Lives
Edit `useGameStore.ts`:
```ts
hearts: 5,      // Changed from 3
maxHearts: 5,
```

### Adjust XP Values
Edit `useGameStore.ts`, in `submitAnswer()`:
```ts
newState.currentXP += 20;  // Was 10 + combo bonus
```

---

## 🐛 Debugging Tips

### See Game State
Open browser DevTools → React DevTools → Find `GameSession`
Check `store` prop to see current state

### Check Stage Config
In RevealStage/MatchingStage components, log:
```tsx
console.log('Stage Config:', config);
```

### Monitor Animations
Framer Motion will log warnings if spring physics are too jarring

---

## 📱 Mobile Testing

### Test on Your Phone
1. Find your machine IP: `ipconfig getifaddr en0` (Mac) or `hostname -I` (Linux)
2. Run dev server with: `npm run dev -- --host`
3. Open: `http://<your-ip>:5173/`

### Test Responsiveness
Chrome DevTools → Toggle Device Toolbar → Select device

---

## 🎬 Key Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `r` | Restart HMR |
| `u` | Show update prompt |
| `c` | Clear console |
| `F12` | Open DevTools |

---

## 💾 Build & Deploy

### Production Build
```bash
npm run build
# Creates dist/ folder with optimized files
```

### Test Production Build Locally
```bash
npm install -g serve
serve dist
# Open http://localhost:3000/
```

### Deploy to Frappe
Copy `dist/` contents to:
```
/home/corex/aurevia-bench/apps/memora/memora/public/
```

Then update Frappe to serve from there.

---

## 🆘 Common Issues

**Issue**: TypeScript errors after editing
```bash
npm run build  # Will show actual errors
```

**Issue**: Styles not loading
```bash
# Clear cache and rebuild
rm -rf node_modules/.vite
npm run dev
```

**Issue**: Mobile layout broken
- Check `h-dvh` vs `h-screen`
- Ensure max-width: 480px on container

**Issue**: Animations feel janky
- Framer Motion might need reduced motion preferences
- Check `prefers-reduced-motion` in browser settings

---

## 📚 Official Docs

- **React**: https://react.dev/
- **Tailwind**: https://tailwindcss.com/
- **Framer Motion**: https://www.framer.com/motion/
- **Zustand**: https://zustand.docs.pmnd.rs/
- **Vite**: https://vitejs.dev/

---

**Ready to build? Good luck! 🚀**
