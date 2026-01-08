import React from 'react';
import { motion } from 'framer-motion';

interface ProgressBarProps {
  current: number;
  total: number;
  variant?: 'primary' | 'secondary' | 'success';
}

/**
 * Animated progress bar for lesson progression
 */
export const ProgressBar: React.FC<ProgressBarProps> = ({
  current,
  total,
  variant = 'primary',
}) => {
  const percentage = Math.min((current / total) * 100, 100);

  const variantMap = {
    primary: 'bg-primary',
    secondary: 'bg-secondary',
    success: 'bg-state-success',
  };

  return (
    <div className="w-full bg-gray-200 rounded-full h-2 overflow-hidden">
      <motion.div
        initial={{ width: '0%' }}
        animate={{ width: `${percentage}%` }}
        transition={{ duration: 0.6, ease: 'easeOut' }}
        className={`h-full ${variantMap[variant]}`}
      />
    </div>
  );
};
