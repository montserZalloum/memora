import { create } from 'zustand';

export type StageType = 'Reveal' | 'Matching' | 'Quiz' | 'Story';

export interface GameStage {
  id: string;
  type: StageType;
  title: string;
  config: any;
}

export interface MatchingConfig {
  instruction: string;
  pairs: Array<{ id: string; left: string; right: string }>;
}

export interface RevealConfig {
  image: string;
  sentence: string;
  highlights: Array<{ word: string; explanation: string }>;
}

interface GameState {
  // Lesson & Queue Management
  lessonId: string | null;
  allStages: GameStage[];
  stageQueue: GameStage[];
  retryQueue: GameStage[];
  currentStageIndex: number;

  // Game Metrics
  currentXP: number;
  comboStreak: number;
  hearts: number;
  maxHearts: number;

  // Game Session State
  isGameActive: boolean;
  isGameWon: boolean;
  isGameOver: boolean;

  // Actions
  loadLesson: (stages: GameStage[]) => void;
  submitAnswer: (isCorrect: boolean) => void;
  resetGame: () => void;
  addXP: (amount: number) => void;
  loseHeart: () => void;
  nextStage: () => void;
}

export const useGameStore = create<GameState>((set) => ({
  // Initial State
  lessonId: null,
  allStages: [],
  stageQueue: [],
  retryQueue: [],
  currentStageIndex: 0,
  currentXP: 0,
  comboStreak: 0,
  hearts: 3,
  maxHearts: 3,
  isGameActive: false,
  isGameWon: false,
  isGameOver: false,

  // Load lesson into queue
  loadLesson: (stages: GameStage[]) => {
    set({
      allStages: stages,
      stageQueue: [...stages],
      retryQueue: [],
      currentStageIndex: 0,
      isGameActive: true,
      isGameWon: false,
      isGameOver: false,
      currentXP: 0,
      comboStreak: 0,
      hearts: 3,
    });
  },

  // Submit answer with Duolingo-style retry logic
  submitAnswer: (isCorrect: boolean) => {
    set((state) => {
      if (!state.isGameActive) return state;

      const currentStage = state.stageQueue[state.currentStageIndex];
      if (!currentStage) return state;

      let newState = { ...state };

      if (isCorrect) {
        // ✅ Correct Answer
        newState.comboStreak += 1;
        newState.currentXP += 10 + (state.comboStreak * 2); // Bonus XP for combo

        // Remove from queue and move to next
        newState.stageQueue = [
          ...state.stageQueue.slice(0, state.currentStageIndex),
          ...state.stageQueue.slice(state.currentStageIndex + 1),
        ];
        newState.currentStageIndex = Math.min(
          state.currentStageIndex,
          Math.max(0, newState.stageQueue.length - 1)
        );

        // Check if lesson is complete
        if (newState.stageQueue.length === 0) {
          newState.isGameActive = false;
          newState.isGameWon = true;
        }
      } else {
        // ❌ Incorrect Answer
        newState.comboStreak = 0;
        newState.hearts -= 1;

        // Move current stage to end of retry queue
        newState.retryQueue.push(currentStage);
        newState.stageQueue = [
          ...state.stageQueue.slice(0, state.currentStageIndex),
          ...state.stageQueue.slice(state.currentStageIndex + 1),
          currentStage, // Push to end
        ];
        newState.currentStageIndex = Math.min(
          state.currentStageIndex,
          Math.max(0, newState.stageQueue.length - 1)
        );

        // Check if game over (0 hearts)
        if (newState.hearts <= 0) {
          newState.isGameActive = false;
          newState.isGameOver = true;
        }
      }

      return newState;
    });
  },

  // Add XP manually
  addXP: (amount: number) => {
    set((state) => ({
      currentXP: state.currentXP + amount,
    }));
  },

  // Lose a heart
  loseHeart: () => {
    set((state) => {
      const newHearts = Math.max(0, state.hearts - 1);
      return {
        hearts: newHearts,
        isGameOver: newHearts === 0,
        isGameActive: newHearts > 0,
      };
    });
  },

  // Move to next stage
  nextStage: () => {
    set((state) => {
      const nextIndex = state.currentStageIndex + 1;
      if (nextIndex >= state.stageQueue.length) {
        return {
          isGameActive: false,
          isGameWon: true,
        };
      }
      return { currentStageIndex: nextIndex };
    });
  },

  // Reset game
  resetGame: () => {
    set({
      lessonId: null,
      allStages: [],
      stageQueue: [],
      retryQueue: [],
      currentStageIndex: 0,
      currentXP: 0,
      comboStreak: 0,
      hearts: 3,
      isGameActive: false,
      isGameWon: false,
      isGameOver: false,
    });
  },
}));
