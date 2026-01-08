import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useGameStore } from '../store/useGameStore';
import type { GameStage } from '../store/useGameStore';
import { Layout } from '../components/Layout';
import { ProgressBar } from '../components/ProgressBar';
import { HeartDisplay } from '../components/HeartDisplay';
import { JuicyButton } from '../components/JuicyButton';
import { RevealStage } from '../components/stages/RevealStage';
import { MatchingStage } from '../components/stages/MatchingStage';
import { Trophy, RotateCcw } from 'lucide-react';

interface GameSessionProps {
  lessonId?: string;
}

/**
 * GameSession Orchestrator
 * Main component that manages the entire game flow
 * - Connects store to stage renderers
 * - Handles win/loss states
 * - Manages progression through stages
 */
export const GameSession: React.FC<GameSessionProps> = ({ lessonId = 'sample' }) => {
  const {
    stageQueue,
    currentStageIndex,
    currentXP,
    comboStreak,
    hearts,
    maxHearts,
    isGameActive,
    isGameWon,
    isGameOver,
    submitAnswer,
    resetGame,
    loadLesson,
  } = useGameStore();

  const [lastHearts, setLastHearts] = useState(hearts);
  const [shouldShakeHearts, setShouldShakeHearts] = useState(false);

  // Mock lesson data - replace with API call
  useEffect(() => {
    const mockLesson: GameStage[] = [
      {
        id: '1',
        type: 'Reveal',
        title: 'تعليم جديد',
        config: {
          image: '📚',
          sentence: 'هذا كتاب جديد وممتع جداً للقراءة',
          highlights: [
            { word: 'كتاب', explanation: 'كتاب هو عمل مكتوب يحتوي على معلومات' },
            { word: 'جديد', explanation: 'جديد يعني حديث الصنع أو لم يستخدم من قبل' },
            { word: 'ممتع', explanation: 'ممتع يعني مثير للاهتمام والتسلية' },
          ],
        },
      },
      {
        id: '2',
        type: 'Matching',
        title: 'طابق الكلمات',
        config: {
          instruction: 'طابق الكلمات مع معانيها',
          pairs: [
            { id: '1', left: 'ماء', right: 'سائل شفاف' },
            { id: '2', left: 'نار', right: 'حرارة وضوء' },
            { id: '3', left: 'أرض', right: 'كوكبنا' },
            { id: '4', left: 'هواء', right: 'نتنفسه دائماً' },
          ],
        },
      },
      {
        id: '3',
        type: 'Reveal',
        title: 'الحروف',
        config: {
          image: '🔤',
          sentence: 'الحروف العربية جميلة وسهلة التعلم',
          highlights: [
            { word: 'الحروف', explanation: 'الحروف هي أساس أي لغة' },
            { word: 'العربية', explanation: 'اللغة العربية من أغنى اللغات' },
            { word: 'جميلة', explanation: 'جميلة تعني حسنة المظهر' },
          ],
        },
      },
    ];

    loadLesson(mockLesson);
  }, [lessonId, loadLesson]);

  // Monitor heart changes for shake animation
  useEffect(() => {
    if (hearts < lastHearts) {
      setShouldShakeHearts(true);
      setTimeout(() => setShouldShakeHearts(false), 500);
    }
    setLastHearts(hearts);
  }, [hearts, lastHearts]);

  const currentStage = stageQueue[currentStageIndex];

  const handleStageComplete = (isCorrect: boolean) => {
    submitAnswer(isCorrect);
  };

  const renderStage = () => {
    if (!currentStage) return null;

    switch (currentStage.type) {
      case 'Reveal':
        return (
          <RevealStage stage={currentStage} onComplete={handleStageComplete} />
        );
      case 'Matching':
        return (
          <MatchingStage stage={currentStage} onComplete={handleStageComplete} />
        );
      default:
        return (
          <div className="flex items-center justify-center h-full">
            <p>نوع المرحلة غير مدعوم</p>
          </div>
        );
    }
  };

  return (
    <Layout>
      {/* Game Active State */}
      {isGameActive && (
        <AnimatePresence mode="wait">
          <motion.div
            key={currentStageIndex}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="h-full flex flex-col"
          >
            {/* Header */}
            <div className="bg-surface-warm p-4 flex justify-between items-center">
              <HeartDisplay
                current={hearts}
                max={maxHearts}
                isShaking={shouldShakeHearts}
              />
              <div className="text-center">
                <p className="text-sm text-gray-600">XP</p>
                <p className="text-xl font-bold text-primary">{currentXP}</p>
              </div>
              <div className="text-center">
                <p className="text-sm text-gray-600">🔥</p>
                <p className="text-xl font-bold text-secondary">{comboStreak}</p>
              </div>
            </div>

            {/* Progress Bar */}
            <div className="px-4 pt-3 pb-2">
              <ProgressBar
                current={stageQueue.length - (stageQueue.length - currentStageIndex - 1)}
                total={stageQueue.length}
                variant="primary"
              />
              <p className="text-xs text-gray-600 text-center mt-1">
                {stageQueue.length - currentStageIndex} من {stageQueue.length}
              </p>
            </div>

            {/* Stage Content */}
            <div className="stage-content">
              {renderStage()}
            </div>
          </motion.div>
        </AnimatePresence>
      )}

      {/* Win State */}
      {isGameWon && (
        <motion.div
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          className="h-full flex flex-col items-center justify-center p-6"
        >
          <motion.div
            animate={{ scale: [1, 1.2, 1] }}
            transition={{ duration: 0.6, repeat: 2 }}
            className="mb-8"
          >
            <Trophy size={80} className="text-secondary" />
          </motion.div>

          <h1 className="text-4xl font-bold text-primary mb-4">مبروك! 🎉</h1>
          <p className="text-xl text-gray-700 mb-2">لقد أكملت الدرس</p>

          <div className="bg-surface-warm p-6 rounded-2xl mb-8 w-full">
            <div className="flex justify-between items-center mb-4">
              <span className="text-gray-600">إجمالي XP</span>
              <span className="text-3xl font-bold text-primary">{currentXP}</span>
            </div>
            <div className="flex justify-between items-center mb-4">
              <span className="text-gray-600">أطول سلسلة</span>
              <span className="text-3xl font-bold text-secondary">{comboStreak}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-600">القلوب المتبقية</span>
              <span className="text-3xl font-bold text-accent">{hearts}</span>
            </div>
          </div>

          <JuicyButton
            onClick={resetGame}
            variant="primary"
            size="lg"
            fullWidth
            className="mb-4"
          >
            درس جديد
          </JuicyButton>

          <JuicyButton
            onClick={() => window.location.href = '/'}
            variant="secondary"
            size="lg"
            fullWidth
          >
            العودة للرئيسية
          </JuicyButton>
        </motion.div>
      )}

      {/* Game Over State */}
      {isGameOver && (
        <motion.div
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          className="h-full flex flex-col items-center justify-center p-6"
        >
          <motion.div
            animate={{ rotate: [0, -10, 10, -10, 0] }}
            transition={{ duration: 0.6 }}
            className="mb-8 text-6xl"
          >
            💔
          </motion.div>

          <h1 className="text-4xl font-bold text-accent mb-4">انتهت القلوب!</h1>
          <p className="text-xl text-gray-700 mb-8">حاول مرة أخرى وستفعل أفضل!</p>

          <div className="bg-surface-warm p-6 rounded-2xl mb-8 w-full">
            <div className="text-center">
              <p className="text-gray-600 mb-2">لقد جمعت</p>
              <p className="text-4xl font-bold text-primary">{currentXP} XP</p>
            </div>
          </div>

          <JuicyButton
            onClick={resetGame}
            variant="primary"
            size="lg"
            fullWidth
            className="mb-4 flex items-center justify-center gap-2"
          >
            <RotateCcw size={20} />
            حاول مرة أخرى
          </JuicyButton>

          <JuicyButton
            onClick={() => window.location.href = '/'}
            variant="secondary"
            size="lg"
            fullWidth
          >
            العودة للرئيسية
          </JuicyButton>
        </motion.div>
      )}
    </Layout>
  );
};
