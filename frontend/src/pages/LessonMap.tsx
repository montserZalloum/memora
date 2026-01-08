import React, { useEffect, useState } from 'react';
import { LoginRequired } from './LoginRequired';

interface Lesson {
  id: string;
  name: string;
  icon: string;
  is_completed: boolean;
  is_locked: boolean;
}

interface LessonMapProps {
  onLessonSelect: (lessonId: string) => void;
}

/**
 * LessonMap - Skill Tree exactly matching the reference HTML
 * Vertical path with circular nodes and connecting lines
 */
export const LessonMap: React.FC<LessonMapProps> = ({ onLessonSelect }) => {
  const [lessons, setLessons] = useState<Lesson[]>([]);
  const [loading, setLoading] = useState(true);
  const [isAuthenticated, setIsAuthenticated] = useState(true);

  useEffect(() => {
    const getCSRFToken = async (): Promise<string> => {
      // First try to get from window (production)
      if ((window as any).csrf_token) {
        return (window as any).csrf_token;
      }

      // In development, try to get from cookies
      try {
        const cookies = document.cookie.split(';');
        const csrfCookie = cookies.find(c => c.trim().startsWith('csrf_token='));
        if (csrfCookie) {
          return csrfCookie.split('=')[1];
        }

        // If no cookie, make a request to get it
        await fetch('/api/method/frappe.auth.get_logged_user', {
          credentials: 'include',
        });

        // Try again to get from cookies
        const newCookies = document.cookie.split(';');
        const newCsrfCookie = newCookies.find(c => c.trim().startsWith('csrf_token='));
        if (newCsrfCookie) {
          return newCsrfCookie.split('=')[1];
        }
      } catch (error) {
        console.warn('Failed to fetch CSRF token:', error);
      }

      return '';
    };

    const fetchLessons = async () => {
      try {
        // Get CSRF token
        const csrfToken = await getCSRFToken();

        const response = await fetch(
          '/api/method/memora.memora.api.get_available_lessons',
          {
            method: 'GET',
            headers: {
              'Content-Type': 'application/json',
              'X-Frappe-CSRF-Token': csrfToken,
            },
            credentials: 'include',
          }
        );

        // Check for authentication errors
        if (response.status === 401 || response.status === 403 || response.status === 417) {
          setIsAuthenticated(false);
          setLoading(false);
          return;
        }

        if (!response.ok) {
          throw new Error(`Failed to fetch lessons: ${response.statusText}`);
        }

        const data = await response.json();
        const lessonData = data.message || [];

        setLessons(lessonData);
        setIsAuthenticated(true);
        setLoading(false);
      } catch (error) {
        console.error('Error fetching lessons:', error);

        // Check if it's an authentication error
        if (error instanceof Error &&
            (error.message.includes('EXPECTATION FAILED') ||
             error.message.includes('UNAUTHORIZED') ||
             error.message.includes('FORBIDDEN'))) {
          setIsAuthenticated(false);
          setLoading(false);
          return;
        }

        // For other errors, fallback to mock data (for development)
        const mockLessons: Lesson[] = [
          {
            id: 'lesson-1',
            name: 'الدرس 1',
            icon: '📖',
            is_completed: false,
            is_locked: false,
          },
          {
            id: 'lesson-2',
            name: 'الدرس 2',
            icon: '🎯',
            is_completed: false,
            is_locked: true,
          },
          {
            id: 'lesson-3',
            name: 'الدرس 3',
            icon: '⭐',
            is_completed: false,
            is_locked: true,
          },
          {
            id: 'lesson-4',
            name: 'الدرس 4',
            icon: '🏆',
            is_completed: false,
            is_locked: true,
          },
        ];

        setLessons(mockLessons);
        setLoading(false);
      }
    };

    fetchLessons();
  }, []);

  const getNodeClass = (lesson: Lesson): string => {
    if (lesson.is_completed) return 'skill-node completed';
    if (lesson.is_locked) return 'skill-node locked';
    return 'skill-node available';
  };

  const handleNodeClick = (lesson: Lesson) => {
    if (!lesson.is_locked) {
      onLessonSelect(lesson.id);
    }
  };

  // Show login screen if not authenticated
  if (!isAuthenticated) {
    return <LoginRequired />;
  }

  if (loading) {
    return (
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        height: '100vh',
        flexDirection: 'column'
      }}>
        <div style={{ fontSize: '60px', marginBottom: '20px' }}>📚</div>
        <p style={{ fontSize: '20px', color: 'var(--text-muted)' }}>جاري التحميل...</p>
      </div>
    );
  }

  return (
    <div style={{
      minHeight: '100vh',
      background: 'var(--bg-cream)',
      overflow: 'auto'
    }}>
      {/* Header - matching reference HTML */}
      <div style={{
        background: 'linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%)',
        padding: '16px 32px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        boxShadow: '0 4px 20px rgba(0, 125, 91, 0.3)',
        position: 'sticky',
        top: 0,
        zIndex: 100
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', color: 'white' }}>
          <div style={{
            width: '48px',
            height: '48px',
            background: 'var(--secondary)',
            borderRadius: '12px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '24px',
            boxShadow: '0 4px 12px rgba(232, 168, 56, 0.4)'
          }}>
            🎓
          </div>
          <h1 style={{
            fontSize: '24px',
            fontWeight: 800,
            textShadow: '0 2px 4px rgba(0,0,0,0.2)'
          }}>
            مذكرة
          </h1>
        </div>

        <div style={{ display: 'flex', gap: '24px', alignItems: 'center' }}>
          {/* XP Stat */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            background: 'rgba(255,255,255,0.15)',
            padding: '8px 16px',
            borderRadius: '20px',
            color: 'white',
            fontWeight: 700,
            fontSize: '18px',
            backdropFilter: 'blur(10px)'
          }}>
            <span style={{ fontSize: '22px' }}>⭐</span>
            <span>0</span>
          </div>

          {/* Gems Stat */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            background: 'rgba(255,255,255,0.15)',
            padding: '8px 16px',
            borderRadius: '20px',
            color: 'white',
            fontWeight: 700,
            fontSize: '18px',
            backdropFilter: 'blur(10px)'
          }}>
            <span style={{ fontSize: '22px' }}>💎</span>
            <span>0</span>
          </div>
        </div>
      </div>

      {/* Skill Tree Title */}
      <div style={{
        fontSize: '32px',
        fontWeight: 800,
        color: 'var(--primary-dark)',
        marginTop: '40px',
        marginBottom: '40px',
        textAlign: 'center'
      }}>
        اختر درساً
      </div>

      {/* Skill Tree - Exact structure from reference HTML */}
      <div className="skill-tree">
        {lessons.map((lesson, index) => (
          <React.Fragment key={lesson.id}>
            {/* Skill Node */}
            <div
              className={getNodeClass(lesson)}
              onClick={() => handleNodeClick(lesson)}
              style={{ position: 'relative' }}
            >
              <div className="skill-icon">{lesson.icon}</div>
              <div className="skill-name">{lesson.name}</div>

              {/* Crown badge for completed lessons */}
              {lesson.is_completed && (
                <div className="crown-badge">👑</div>
              )}

              {/* Lock icon for locked lessons */}
              {lesson.is_locked && (
                <div style={{
                  position: 'absolute',
                  top: '50%',
                  left: '50%',
                  transform: 'translate(-50%, -50%)',
                  fontSize: '40px'
                }}>
                  🔒
                </div>
              )}
            </div>

            {/* Connector Line (except after last node) */}
            {index < lessons.length - 1 && (
              <div className={lesson.is_locked ? 'skill-connector locked' : 'skill-connector'} />
            )}
          </React.Fragment>
        ))}
      </div>
    </div>
  );
};
