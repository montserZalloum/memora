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

// Interaction tracking per the API contract
export interface StageInteraction {
  question_id: string;
  type: string;
  attempts_count: number;
  duration_ms: number;
  is_final_outcome_correct: boolean;
  mistake_details?: string;
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

  // Session Tracking
  sessionStartTime: string | null;
  interactions: StageInteraction[];
  currentStageStartTime: number | null;
  currentStageAttempts: number;

  // Loading & Error States
  isLoading: boolean;
  error: string | null;

  // Actions
  fetchLessonContent: (lessonId: string) => Promise<void>;
  loadLesson: (stages: GameStage[]) => void;
  submitAnswer: (isCorrect: boolean) => void;
  submitSession: () => Promise<void>;
  resetGame: () => void;
  addXP: (amount: number) => void;
  loseHeart: () => void;
  nextStage: () => void;
  startStageTimer: () => void;
}

// Helper to get csrf_token from window (Frappe convention)
const getCSRFToken = async (): Promise<string> => {
  // First try to get from window (production)
  if ((window as any).csrf_token) {
    return (window as any).csrf_token;
  }

  // In development, fetch from Frappe API
  try {
    const response = await fetch('/api/method/frappe.auth.get_logged_user', {
      credentials: 'include', // Important: include cookies
    });

    if (response.ok) {
      // The CSRF token is in the response headers or cookies
      const cookies = document.cookie.split(';');
      const csrfCookie = cookies.find(c => c.trim().startsWith('csrf_token='));
      if (csrfCookie) {
        return csrfCookie.split('=')[1];
      }
    }
  } catch (error) {
    console.warn('Failed to fetch CSRF token:', error);
  }

  return '';
};

export const useGameStore = create<GameState>((set, get) => ({
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
  sessionStartTime: null,
  interactions: [],
  currentStageStartTime: null,
  currentStageAttempts: 0,
  isLoading: false,
  error: null,

  // Fetch lesson content from Frappe API
  fetchLessonContent: async (lessonId: string) => {
    set({ isLoading: true, error: null });

    try {
      const csrfToken = await getCSRFToken();

      const response = await fetch(
        `/api/method/memora.memora.api.get_lesson_content?lesson_id=${lessonId}`,
        {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
            'X-Frappe-CSRF-Token': csrfToken,
          },
          credentials: 'include', // Include cookies for auth
        }
      );

      if (!response.ok) {
        throw new Error(`Failed to fetch lesson: ${response.statusText}`);
      }

      const data = await response.json();

      // Frappe API wraps response in { message: {...} }
      const lessonData = data.message;

      // Load the stages into the game
      get().loadLesson(lessonData.stages || []);
      set({ lessonId, isLoading: false });
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      set({ error: errorMessage, isLoading: false });
      console.error('Error fetching lesson:', error);
    }
  },

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
      sessionStartTime: new Date().toISOString(),
      interactions: [],
      currentStageStartTime: Date.now(),
      currentStageAttempts: 0,
    });
  },

  // Start timer for current stage
  startStageTimer: () => {
    set({
      currentStageStartTime: Date.now(),
      currentStageAttempts: 0,
    });
  },

  // Submit answer with Duolingo-style retry logic
  submitAnswer: (isCorrect: boolean) => {
    set((state) => {
      if (!state.isGameActive) return state;

      const currentStage = state.stageQueue[state.currentStageIndex];
      if (!currentStage) return state;

      // Calculate duration
      const duration_ms = state.currentStageStartTime
        ? Date.now() - state.currentStageStartTime
        : 0;
      const attempts_count = state.currentStageAttempts + 1;

      // Record this interaction
      const interaction: StageInteraction = {
        question_id: currentStage.id,
        type: currentStage.type,
        attempts_count,
        duration_ms,
        is_final_outcome_correct: isCorrect,
        ...(isCorrect ? {} : { mistake_details: 'incorrect_answer' }),
      };

      let newState = { ...state };
      newState.interactions = [...state.interactions, interaction];

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

        // Reset stage timer for next stage
        newState.currentStageStartTime = Date.now();
        newState.currentStageAttempts = 0;

        // Check if lesson is complete
        if (newState.stageQueue.length === 0) {
          newState.isGameActive = false;
          newState.isGameWon = true;
        }
      } else {
        // ❌ Incorrect Answer - increment attempt counter
        newState.currentStageAttempts += 1;
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

        // Reset timer for current (next) stage
        newState.currentStageStartTime = Date.now();
        newState.currentStageAttempts = 0;

        // Check if game over (0 hearts)
        if (newState.hearts <= 0) {
          newState.isGameActive = false;
          newState.isGameOver = true;
        }
      }

      return newState;
    });
  },

  // Submit session to Frappe backend
  submitSession: async () => {
    const state = get();

    if (!state.lessonId || !state.sessionStartTime) {
      console.error('Cannot submit session: missing lesson ID or start time');
      return;
    }

    const payload = {
      session_meta: {
        lesson_id: state.lessonId,
        start_timestamp: state.sessionStartTime,
        end_timestamp: new Date().toISOString(),
        device_info: navigator.userAgent,
      },
      gamification_results: {
        xp_earned: state.currentXP,
        gems_collected: 0, // Can be added later
      },
      interactions: state.interactions,
    };

    try {
      const csrfToken = await getCSRFToken();

      const response = await fetch(
        '/api/method/memora.memora.api.submit_session',
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-Frappe-CSRF-Token': csrfToken,
          },
          credentials: 'include', // Include cookies for auth
          body: JSON.stringify(payload),
        }
      );

      if (!response.ok) {
        throw new Error(`Failed to submit session: ${response.statusText}`);
      }

      const data = await response.json();
      console.log('Session submitted successfully:', data);
    } catch (error) {
      console.error('Error submitting session:', error);
      set({ error: error instanceof Error ? error.message : 'Submission failed' });
    }
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
      sessionStartTime: null,
      interactions: [],
      currentStageStartTime: null,
      currentStageAttempts: 0,
      isLoading: false,
      error: null,
    });
  },
}));
