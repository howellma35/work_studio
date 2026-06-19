import React, { Component, ErrorInfo, ReactNode } from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './index.css';

// 错误边界：防止 CopilotKit 连接失败导致整个页面白屏
class ErrorBoundary extends Component<{ children: ReactNode }, { hasError: boolean; error: string }> {
  state = { hasError: false, error: '' };
  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error: error.message };
  }
  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('ErrorBoundary caught:', error, info);
  }
  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: 40, color: '#f87171', fontFamily: 'monospace', background: '#0f172a', minHeight: '100vh' }}>
          <h2>页面渲染出错</h2>
          <pre style={{ whiteSpace: 'pre-wrap', marginTop: 16 }}>{this.state.error}</pre>
          <button
            onClick={() => this.setState({ hasError: false, error: '' })}
            style={{ marginTop: 16, padding: '8px 16px', cursor: 'pointer' }}
          >
            重试
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </React.StrictMode>
);
