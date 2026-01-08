import React from 'react';

/**
 * LoginRequired - Shows when user is not authenticated
 * Matches the Juicy design from reference HTML
 */
export const LoginRequired: React.FC = () => {
  const handleLogin = () => {
    // Redirect to production login page
    window.location.href = 'https://x.conanacademy.com/login';
  };

  return (
    <div style={{
      minHeight: '100vh',
      background: 'var(--bg-cream)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '32px'
    }}>
      <div style={{
        background: 'white',
        borderRadius: 'var(--border-radius-lg)',
        padding: '60px 40px',
        boxShadow: 'var(--card-shadow)',
        maxWidth: '500px',
        width: '100%',
        textAlign: 'center'
      }}>
        {/* Icon */}
        <div style={{
          fontSize: '80px',
          marginBottom: '24px',
          animation: 'pulse 2s infinite'
        }}>
          🔒
        </div>

        {/* Title */}
        <h1 style={{
          fontSize: '32px',
          fontWeight: 800,
          color: 'var(--primary-dark)',
          marginBottom: '16px'
        }}>
          تسجيل الدخول مطلوب
        </h1>

        {/* Description */}
        <p style={{
          fontSize: '18px',
          color: 'var(--text-muted)',
          marginBottom: '32px',
          lineHeight: 1.6
        }}>
          يجب تسجيل الدخول للوصول إلى الدروس التعليمية
        </p>

        {/* Login Button */}
        <button
          onClick={handleLogin}
          style={{
            background: 'linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%)',
            color: 'white',
            border: 'none',
            padding: '16px 48px',
            fontSize: '20px',
            fontWeight: 700,
            borderRadius: '30px',
            cursor: 'pointer',
            transition: 'var(--transition)',
            boxShadow: '0 4px 15px rgba(0, 125, 91, 0.4)',
            fontFamily: "'Tajawal', sans-serif",
            width: '100%'
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.transform = 'translateY(-2px)';
            e.currentTarget.style.boxShadow = '0 6px 20px rgba(0, 125, 91, 0.5)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.transform = 'translateY(0)';
            e.currentTarget.style.boxShadow = '0 4px 15px rgba(0, 125, 91, 0.4)';
          }}
        >
          تسجيل الدخول
        </button>

        {/* Info */}
        <p style={{
          marginTop: '24px',
          fontSize: '14px',
          color: 'var(--text-muted)'
        }}>
          سيتم توجيهك إلى صفحة تسجيل الدخول
        </p>
      </div>
    </div>
  );
};
