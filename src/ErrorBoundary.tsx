// ============================================================
// src/ErrorBoundary.tsx — Отлов ошибок рендеринга
// ============================================================

import { Component, ErrorInfo, ReactNode } from 'react';

interface ErrorBoundaryProps {
  children: ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(_error: Error): Partial<ErrorBoundaryState> {
    return { hasError: true };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('ErrorBoundary caught an error:', error, errorInfo);
    this.setState({
      error: error,
      errorInfo: errorInfo
    });
  }

  handleReload = () => {
    window.location.reload();
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-[#fdf4ed] to-[#f7e4d4] p-4">
          <div className="bg-white/80 backdrop-blur-xl rounded-2xl shadow-xl p-6 max-w-md w-full text-center liquid-glass-calendar">
            <div className="text-6xl mb-4">😕</div>
            <h1 className="text-2xl font-bold text-[#3d2b1f] mb-2">
              Что-то пошло не так
            </h1>
            <p className="text-[#9e8476] mb-4">
              Произошла ошибка при загрузке приложения.
            </p>
            {this.state.error && (
              <details className="mb-4 text-left">
                <summary className="cursor-pointer text-sm text-[#9e8476] hover:text-[#3d2b1f]">
                  Показать детали ошибки
                </summary>
                <pre className="mt-2 p-3 bg-[#f7e4d4]/50 rounded-lg text-xs overflow-auto max-h-40">
                  {this.state.error.toString()}
                  {this.state.errorInfo && this.state.errorInfo.componentStack}
                </pre>
              </details>
            )}
            <button
              onClick={this.handleReload}
              className="bg-[#c4967a] hover:bg-[#b0856a] text-white font-medium py-3 px-6 rounded-xl transition-colors"
            >
              Перезагрузить
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
