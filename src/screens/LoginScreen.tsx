import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { AuthError } from '../api/auth'
import { useAuth } from '../context/AuthContext'
import { resolvePostLoginRoute } from '../utils/postLoginRoute'

export function LoginScreen() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const { login } = useAuth()
  const navigate = useNavigate()

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    setIsLoading(true)
    setError(null)
    try {
      await login(email, password)
      const destination = await resolvePostLoginRoute()
      navigate(destination, { replace: true })
    } catch (err) {
      setError(err instanceof AuthError ? err.message : 'Something went wrong. Please try again.')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <main className="w-full pt-20 lg:pt-12 bg-surface min-h-screen flex items-center justify-center">
      <div className="w-full max-w-[420px] lg:max-w-[460px] 2xl:max-w-[500px] px-margin-mobile">
        <div className="text-center mb-8 lg:mb-10">
          <img
            src="/brand/dispatch-mark-bold.png"
            alt=""
            aria-hidden="true"
            className="h-16 w-16 lg:h-[76px] lg:w-[76px] 2xl:h-[84px] 2xl:w-[84px] object-contain mx-auto mb-5 lg:mb-6"
          />
          <h1 className="font-serif text-display-mobile lg:text-[40px] 2xl:text-[44px] text-on-surface tracking-tight leading-tight mb-2 lg:mb-3">
            Welcome back
          </h1>
          <p className="font-serif text-body-md lg:text-[17px] 2xl:text-[19px] text-on-surface-variant">
            Sign in to continue to your brief.
          </p>
        </div>

        <form
          onSubmit={handleSubmit}
          className="bg-surface-container-lowest rounded-xl p-6 lg:p-7 2xl:p-8 shadow-sm border border-surface-container space-y-4"
        >
          <div>
            <label htmlFor="email" className="block font-sans text-label-sm text-on-surface-variant mb-1">
              Email
            </label>
            <input
              id="email"
              type="email"
              required
              autoComplete="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              className="w-full bg-surface-container-low rounded-lg px-4 py-3 lg:py-4 font-sans text-body-md text-on-surface focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>
          <div>
            <label htmlFor="password" className="block font-sans text-label-sm text-on-surface-variant mb-1">
              Password
            </label>
            <div className="relative">
              <input
                id="password"
                type={showPassword ? 'text' : 'password'}
                required
                autoComplete="current-password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                className="w-full bg-surface-container-low rounded-lg px-4 py-3 lg:py-4 pr-11 font-sans text-body-md text-on-surface focus:outline-none focus:ring-2 focus:ring-primary"
              />
              <button
                type="button"
                onClick={() => setShowPassword((prev) => !prev)}
                aria-label={showPassword ? 'Hide password' : 'Show password'}
                className="absolute inset-y-0 right-0 flex items-center px-3 text-on-surface-variant hover:text-on-surface transition-colors cursor-pointer"
              >
                <span className="material-symbols-outlined text-[20px]" aria-hidden="true">
                  {showPassword ? 'visibility_off' : 'visibility'}
                </span>
              </button>
            </div>
          </div>

          {error && (
            <p role="alert" className="font-sans text-label-md text-secondary">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={isLoading}
            className="w-full px-6 py-3 lg:py-4 2xl:py-[18px] bg-primary hover:bg-primary-container text-on-primary rounded-lg font-sans text-label-lg uppercase tracking-wider transition-all shadow-md hover:shadow-xl cursor-pointer disabled:opacity-60 disabled:cursor-not-allowed"
          >
            {isLoading ? 'Signing in…' : 'Sign in'}
          </button>
        </form>

        <p className="text-center font-sans text-label-md text-on-surface-variant mt-6 lg:mt-7">
          Don&apos;t have an account?{' '}
          <Link to="/register" className="text-secondary font-semibold hover:underline">
            Register
          </Link>
        </p>
      </div>
    </main>
  )
}
