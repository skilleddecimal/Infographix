export function Header() {
  return (
    <header className="bg-white border-b border-gray-200">
      <div className="container mx-auto px-4">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-primary-600 rounded-lg flex items-center justify-center">
              <svg
                className="w-5 h-5 text-white"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 17V7m0 10a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h2a2 2 0 012 2m0 10a2 2 0 002 2h2a2 2 0 002-2M9 7a2 2 0 012-2h2a2 2 0 012 2m0 10V7m0 10a2 2 0 002 2h2a2 2 0 002-2V7a2 2 0 00-2-2h-2a2 2 0 00-2 2"
                />
              </svg>
            </div>
            <span className="text-xl font-semibold text-gray-900">
              Infographix
            </span>
          </div>

          {/* Navigation */}
          <nav className="hidden md:flex items-center gap-6">
            <a href="#" className="text-gray-600 hover:text-gray-900">
              Templates
            </a>
            <a href="#" className="text-gray-600 hover:text-gray-900">
              Pricing
            </a>
            <a href="#" className="text-gray-600 hover:text-gray-900">
              Docs
            </a>
          </nav>

          {/* Auth */}
          <div className="flex items-center gap-3">
            <button className="text-gray-600 hover:text-gray-900">
              Sign In
            </button>
            <button className="px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg font-medium transition-colors">
              Get Started
            </button>
          </div>
        </div>
      </div>
    </header>
  )
}
