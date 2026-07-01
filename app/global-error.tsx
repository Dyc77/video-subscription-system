'use client'

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  return (
    <html>
      <body>
        <div style={{
          padding: '40px',
          textAlign: 'center',
          fontFamily: 'system-ui, -apple-system, sans-serif',
          minHeight: '100vh',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          alignItems: 'center',
          backgroundColor: '#1a1f35',
          color: '#ffffff'
        }}>
          <h2 style={{ fontSize: '24px', marginBottom: '16px' }}>發生錯誤</h2>
          <p style={{ marginBottom: '24px', color: '#94a3b8' }}>
            {error.message || '應用程式發生未預期的錯誤'}
          </p>
          <button
            onClick={() => reset()}
            style={{
              padding: '12px 24px',
              cursor: 'pointer',
              backgroundColor: '#3b82f6',
              color: '#ffffff',
              border: 'none',
              borderRadius: '6px',
              fontSize: '16px',
              fontWeight: '500'
            }}
          >
            重新載入
          </button>
        </div>
      </body>
    </html>
  )
}
