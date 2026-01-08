import React from 'react';

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
 * "Juicy" button - Exact styling from reference HTML
 * Uses inline styles to match the continue-btn class
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
  const getBackgroundStyle = () => {
    if (disabled) {
      return { background: '#ccc' };
    }

    switch (variant) {
      case 'primary':
        return {
          background: 'linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%)'
        };
      case 'secondary':
        return {
          background: 'linear-gradient(135deg, var(--secondary) 0%, #D4940A 100%)'
        };
      case 'accent':
        return {
          background: 'linear-gradient(135deg, var(--accent) 0%, #C0392B 100%)'
        };
      case 'success':
        return {
          background: 'linear-gradient(135deg, var(--success) 0%, #00A085 100%)'
        };
      case 'error':
        return {
          background: 'linear-gradient(135deg, var(--error) 0%, #C0392B 100%)'
        };
      default:
        return {
          background: 'linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%)'
        };
    }
  };

  const getSizeStyle = () => {
    switch (size) {
      case 'sm':
        return { padding: '12px 32px', fontSize: '16px' };
      case 'md':
        return { padding: '14px 40px', fontSize: '18px' };
      case 'lg':
        return { padding: '16px 48px', fontSize: '20px' };
      default:
        return { padding: '16px 48px', fontSize: '20px' };
    }
  };

  const baseStyle: React.CSSProperties = {
    color: 'white',
    border: 'none',
    fontWeight: 700,
    borderRadius: '30px',
    cursor: disabled ? 'not-allowed' : 'pointer',
    marginTop: '24px',
    transition: 'var(--transition)',
    boxShadow: disabled ? 'none' : '0 4px 15px rgba(0, 125, 91, 0.4)',
    fontFamily: "'Tajawal', sans-serif",
    width: fullWidth ? '100%' : 'auto',
    ...getBackgroundStyle(),
    ...getSizeStyle(),
  };

  const handleMouseEnter = (e: React.MouseEvent<HTMLButtonElement>) => {
    if (!disabled) {
      e.currentTarget.style.transform = 'translateY(-2px)';
      e.currentTarget.style.boxShadow = '0 6px 20px rgba(0, 125, 91, 0.5)';
    }
  };

  const handleMouseLeave = (e: React.MouseEvent<HTMLButtonElement>) => {
    if (!disabled) {
      e.currentTarget.style.transform = 'translateY(0)';
      e.currentTarget.style.boxShadow = '0 4px 15px rgba(0, 125, 91, 0.4)';
    }
  };

  return (
    <button
      onClick={onClick}
      disabled={disabled}
      style={baseStyle}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      className={className}
    >
      {children}
    </button>
  );
};
