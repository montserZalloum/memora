import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import type { GameStage, RevealConfig } from '../../store/useGameStore';
import { JuicyButton } from '../JuicyButton';
import { X } from 'lucide-react';

interface RevealStageProps {
  stage: GameStage;
  onComplete: (isCorrect: boolean) => void;
}

/**
 * Reveal Stage: Interactive word highlighting with bottom-sheet explanations
 * User clicks on highlighted words to see explanations
 */
export const RevealStage: React.FC<RevealStageProps> = ({ stage, onComplete }) => {
  const config = stage.config as RevealConfig;
  const [expandedWord, setExpandedWord] = useState<string | null>(null);
  const [revealed, setRevealed] = useState<Set<string>>(new Set());

  const handleWordClick = (word: string) => {
    const newRevealed = new Set(revealed);
    newRevealed.add(word);
    setRevealed(newRevealed);
    setExpandedWord(word);
  };

  const handleComplete = () => {
    // Mark as correct if all words are revealed
    const allRevealed = config.highlights.length === revealed.size;
    onComplete(allRevealed);
  };

  const renderSentenceWithHighlights = () => {
    const words = config.sentence.split(' ');

    return words.map((word, index) => {
      const cleanWord = word.replace(/[.,!?]/g, '');
      const isHighlighted = config.highlights.some(
        (h) => h.word.toLowerCase() === cleanWord.toLowerCase()
      );

      if (isHighlighted) {
        return (
          <motion.button
            key={index}
            onClick={() => handleWordClick(cleanWord)}
            whileHover={{ scale: 1.1 }}
            whileTap={{ scale: 0.95 }}
            className={`inline-block mx-1 px-3 py-2 rounded-lg font-bold transition-all ${
              revealed.has(cleanWord)
                ? 'bg-primary text-white'
                : 'bg-secondary text-white hover:bg-secondary-light'
            }`}
          >
            {word}
          </motion.button>
        );
      }

      return (
        <span key={index} className="mx-1">
          {word}
        </span>
      );
    });
  };

  const selectedHighlight = config.highlights.find(
    (h) => h.word.toLowerCase() === expandedWord?.toLowerCase()
  );

  return (
    <div className="h-full flex flex-col items-center justify-between p-6">
      {/* Emoji/Image */}
      <motion.div
        initial={{ scale: 0 }}
        animate={{ scale: 1 }}
        transition={{ type: 'spring', stiffness: 100, damping: 15 }}
        className="text-7xl mb-8"
      >
        {config.image}
      </motion.div>

      {/* Title */}
      <h2 className="text-2xl font-bold text-center mb-8">{stage.title}</h2>

      {/* Interactive Sentence */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="flex flex-wrap justify-center gap-2 mb-12 px-4"
      >
        {renderSentenceWithHighlights()}
      </motion.div>

      {/* Bottom Sheet Explanation */}
      <AnimatePresence>
        {selectedHighlight && (
          <motion.div
            initial={{ y: 300, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            exit={{ y: 300, opacity: 0 }}
            transition={{ type: 'spring', stiffness: 300, damping: 30 }}
            className="fixed bottom-0 left-0 right-0 bg-surface-cream p-6 rounded-t-3xl shadow-lg"
            style={{ maxWidth: '480px', margin: '0 auto' }}
          >
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-xl font-bold text-primary">{expandedWord}</h3>
              <button
                onClick={() => setExpandedWord(null)}
                className="p-2 hover:bg-gray-200 rounded-full"
              >
                <X size={24} />
              </button>
            </div>
            <p className="text-gray-700 text-lg leading-relaxed">
              {selectedHighlight.explanation}
            </p>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Continue Button */}
      <JuicyButton
        onClick={handleComplete}
        variant={revealed.size === config.highlights.length ? 'success' : 'primary'}
        size="lg"
        fullWidth
      >
        {revealed.size === config.highlights.length ? '✓ فهمت' : 'متابعة'}
      </JuicyButton>
    </div>
  );
};
