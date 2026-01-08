/**
 * Shared TypeScript Types for Jordan Project
 * Re-exported from useGameStore for convenience
 */

export type { StageType, GameStage, MatchingConfig, RevealConfig } from '../store/useGameStore';

import type { GameStage } from '../store/useGameStore';

/**
 * Example API Response Types (for Frappe Integration)
 */
export interface LessonResponse {
  name: string;
  title: string;
  description: string;
  stages: GameStage[];
  difficulty: 'easy' | 'medium' | 'hard';
  estimated_time: number; // in minutes
}

export interface ProgressResponse {
  name: string;
  user: string;
  lesson_id: string;
  xp_earned: number;
  completion_percentage: number;
  completed_at: string;
}

export interface UserProfileResponse {
  name: string;
  user_type: string;
  total_xp: number;
  current_streak: number;
  lessons_completed: number;
  accuracy_rate: number; // 0-100
}

/**
 * Game Session State - Safe to serialize/deserialize
 */
export interface GameSessionSnapshot {
  timestamp: number;
  lessonId: string;
  stageQueue: GameStage[];
  currentStageIndex: number;
  currentXP: number;
  comboStreak: number;
  hearts: number;
  maxHearts: number;
  isGameActive: boolean;
  isGameWon: boolean;
  isGameOver: boolean;
}

/**
 * Utility type for form submissions
 */
export interface AnswerSubmission {
  stageId: string;
  answer: unknown; // Type depends on stage type
  isCorrect: boolean;
  xpEarned: number;
  timestamp: number;
}
