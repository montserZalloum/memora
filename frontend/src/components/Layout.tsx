import React, { useEffect } from 'react';

interface LayoutProps {
  children: React.ReactNode;
}

/**
 * Mobile-first Layout wrapper for the game interface
 * Handles RTL direction, viewport constraints, and dark mode preferences
 */
export const Layout: React.FC<LayoutProps> = ({ children }) => {
  useEffect(() => {
    // Force RTL direction
    document.documentElement.dir = 'rtl';
    document.documentElement.lang = 'ar';
  }, []);

  return (
    <div className="game-container">
      <div className="flex-1 overflow-hidden flex flex-col">
        {children}
      </div>
    </div>
  );
};
