import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { Heart } from 'lucide-react';

interface HeartDisplayProps {
  current: number;
  max: number;
  isShaking?: boolean;
}

/**
 * Heart display with shake animation when damaged
 * Shows filled hearts for remaining lives
 */
export const HeartDisplay: React.FC<HeartDisplayProps> = ({
  current,
  max,
  isShaking = false,
}) => {
  const [trigger, setTrigger] = useState(0);

  useEffect(() => {
    if (isShaking) {
      setTrigger((prev) => prev + 1);
    }
  }, [isShaking]);

  return (
    <motion.div
      animate={isShaking ? { x: [-5, 5, -5, 5, 0] } : { x: 0 }}
      transition={{ duration: 0.5 }}
      key={trigger}
      className="flex gap-2"
    >
      {Array.from({ length: max }).map((_, index) => (
        <motion.div
          key={index}
          initial={{ scale: 1 }}
          animate={index < current ? { scale: 1 } : { scale: 0.8 }}
          transition={{ duration: 0.3 }}
        >
          <Heart
            size={28}
            className={`transition-all ${
              index < current
                ? 'fill-accent text-accent'
                : 'text-gray-300 fill-gray-200'
            }`}
          />
        </motion.div>
      ))}
    </motion.div>
  );
};
