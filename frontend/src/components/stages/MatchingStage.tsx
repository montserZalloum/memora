import React, { useState } from 'react';
import { motion } from 'framer-motion';
import type { GameStage, MatchingConfig } from '../../store/useGameStore';
import { JuicyButton } from '../JuicyButton';

interface PairMatch {
  leftId: string;
  rightId: string;
}

interface MatchingStageProps {
  stage: GameStage;
  onComplete: (isCorrect: boolean) => void;
}

/**
 * Matching Stage: Grid layout with item selection and pairing
 * User connects left items to right items
 */
export const MatchingStage: React.FC<MatchingStageProps> = ({ stage, onComplete }) => {
  const config = stage.config as MatchingConfig;
  const [selectedLeft, setSelectedLeft] = useState<string | null>(null);
  const [matches, setMatches] = useState<PairMatch[]>([]);
  const [errors, setErrors] = useState<Set<string>>(new Set());

  // Shuffle right items for better UX
  const [rightItems] = useState(() => {
    const shuffled = [...config.pairs].sort(() => Math.random() - 0.5);
    return shuffled;
  });

  const handleLeftClick = (leftId: string) => {
    setSelectedLeft(selectedLeft === leftId ? null : leftId);
  };

  const handleRightClick = (rightId: string) => {
    if (!selectedLeft) return;

    const leftPair = config.pairs.find((p) => p.id === selectedLeft);
    const rightPair = config.pairs.find((p) => p.id === rightId);

    if (!leftPair || !rightPair) return;

    // Check if match is correct
    const isCorrectMatch = leftPair.right === rightPair.right;

    if (isCorrectMatch) {
      // Correct match
      const newMatches = [...matches, { leftId: selectedLeft, rightId }];
      setMatches(newMatches);
      setSelectedLeft(null);

      // If all pairs matched, mark as complete
      if (newMatches.length === config.pairs.length) {
        onComplete(true);
      }
    } else {
      // Wrong match
      setErrors(new Set([...errors, `${selectedLeft}-${rightId}`]));
      setSelectedLeft(null);

      // Auto-clear error after 500ms
      setTimeout(() => {
        setErrors((prev) => {
          const next = new Set(prev);
          next.delete(`${selectedLeft}-${rightId}`);
          return next;
        });
      }, 500);
    }
  };

  const isMatched = (leftId: string) =>
    matches.some((m) => m.leftId === leftId);

  const getMatchedRight = (leftId: string) =>
    matches.find((m) => m.leftId === leftId)?.rightId;

  const isRightMatched = (rightId: string) =>
    matches.some((m) => m.rightId === rightId);

  return (
    <div className="h-full flex flex-col p-6">
      {/* Title */}
      <h2 className="text-2xl font-bold text-center mb-4">{stage.title}</h2>
      <p className="text-center text-gray-600 mb-6">{config.instruction}</p>

      {/* Progress */}
      <div className="text-center text-sm font-bold text-primary mb-6">
        {matches.length} / {config.pairs.length}
      </div>

      {/* Grid Layout */}
      <div className="flex-1 flex gap-4 overflow-hidden">
        {/* Left Column */}
        <div className="flex-1 overflow-y-auto space-y-3">
          {config.pairs.map((pair) => {
            const isSelected = selectedLeft === pair.id;
            const isCompleted = isMatched(pair.id);

            return (
              <motion.button
                key={pair.id}
                onClick={() => !isCompleted && handleLeftClick(pair.id)}
                disabled={isCompleted}
                whileHover={!isCompleted ? { scale: 1.05 } : {}}
                whileTap={!isCompleted ? { scale: 0.95 } : {}}
                className={`w-full p-4 rounded-lg font-bold text-center transition-all ${
                  isCompleted
                    ? 'bg-state-success text-white opacity-60'
                    : isSelected
                    ? 'bg-primary text-white scale-105'
                    : 'bg-surface-warm text-gray-800 hover:bg-secondary'
                }`}
              >
                {pair.left}
              </motion.button>
            );
          })}
        </div>

        {/* Right Column */}
        <div className="flex-1 overflow-y-auto space-y-3">
          {rightItems.map((pair) => {
            const isSelected =
              selectedLeft && getMatchedRight(selectedLeft) === pair.id;
            const isCompleted = isRightMatched(pair.id);
            const isError = errors.has(`${selectedLeft}-${pair.id}`);

            return (
              <motion.button
                key={`right-${pair.id}`}
                onClick={() => !isCompleted && handleRightClick(pair.id)}
                disabled={isCompleted}
                whileHover={!isCompleted ? { scale: 1.05 } : {}}
                whileTap={!isCompleted ? { scale: 0.95 } : {}}
                animate={isError ? { x: [-10, 10, -10, 10, 0] } : { x: 0 }}
                transition={{ duration: 0.5 }}
                className={`w-full p-4 rounded-lg font-bold text-center transition-all ${
                  isCompleted
                    ? 'bg-state-success text-white opacity-60'
                    : isError
                    ? 'bg-state-error text-white'
                    : isSelected
                    ? 'bg-primary text-white scale-105'
                    : 'bg-surface-warm text-gray-800 hover:bg-secondary'
                }`}
              >
                {pair.right}
              </motion.button>
            );
          })}
        </div>
      </div>

      {/* Continue Button (only when not complete) */}
      {matches.length < config.pairs.length && (
        <JuicyButton
          onClick={() => onComplete(false)}
          variant="primary"
          size="md"
          fullWidth
          className="mt-4"
        >
          تخطي
        </JuicyButton>
      )}
    </div>
  );
};
