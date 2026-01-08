import React from 'react';
import { motion } from 'framer-motion';
import clsx from 'clsx';

interface JuicyButtonProps {
  onClick?: () => void;
  disabled?: boolean;
  variant?: 'primary' | 'secondary' | 'accent' | 'success' | 'error';
  size?: 'sm' | 'md' | 'lg';
  children: React.ReactNode;
  className?: string;
  fullWidth?: boolean;
}

/**
 * "Juicy" button with 3D shadow effect and satisfying press animation
 * Mimics the feel of Duolingo and other gamified UIs
 */
export const JuicyButton: React.FC<JuicyButtonProps> = ({
  onClick,
  disabled = false,
  variant = 'primary',
  size = 'md',
  children,
  className,
  fullWidth = false,
}) => {
  const colorMap = {
    primary: 'bg-primary text-white shadow-button hover:bg-primary-dark',
    secondary: 'bg-secondary text-white shadow-button hover:bg-secondary-light',
    accent: 'bg-accent text-white shadow-button hover:bg-accent',
    success: 'bg-state-success text-white shadow-button hover:opacity-90',
    error: 'bg-state-error text-white shadow-button hover:opacity-90',
  };

  const sizeMap = {
    sm: 'px-3 py-2 text-sm',
    md: 'px-6 py-3 text-base',
    lg: 'px-8 py-4 text-lg',
  };

  return (
    <motion.button
      onClick={onClick}
      disabled={disabled}
      whileHover={!disabled ? { scale: 1.05 } : {}}
      whileTap={!disabled ? { y: 4, boxShadow: '0 0px 0px rgba(0, 90, 66, 1)' } : {}}
      transition={{ type: 'spring', stiffness: 400, damping: 17 }}
      className={clsx(
        'rounded-full font-tajawal font-bold transition-all duration-75',
        'focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2',
        colorMap[variant],
        sizeMap[size],
        fullWidth && 'w-full',
        disabled && 'opacity-50 cursor-not-allowed',
        className
      )}
    >
      {children}
    </motion.button>
  );
};
