import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { AuthError } from '../api/auth'
import { useAuth } from '../context/AuthContext'

export function RegisterScreen() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const { register } = useAuth()
  const navigate = useNavigate()

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    setIsLoading(true)
    setError(null)
    try {
      await register(email, password)
      navigate('/setup', { replace: true })
    } catch (err) {
      setError(err instanceof AuthError ? err.message : 'Something went wrong. Please try again.')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <main className="w-full pt-20 bg-surface min-h-screen flex items-center justify-center">
      <div className="w-full max-w-[420px] px-margin-mobile">
        <div className="text-center mb-8">
          <h1 className="font-serif text-display-mobile text-on-surface tracking-tight mb-2">
            Create your account
          </h1>
          <p className="font-serif text-body-md text-on-surface-variant">
            Set up Dispatch to follow what matters to you.
          </p>
        </div>

        <form
          onSubmit={handleSubmit}
          className="bg-surface-container-lowest rounded-xl p-6 shadow-sm border border-surface-container space-y-4"
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
              className="w-full bg-surface-container-low rounded-lg px-4 py-3 font-sans text-body-md text-on-surface focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>
          <div>
            <label htmlFor="password" className="block font-sans text-label-sm text-on-surface-variant mb-1">
              Password
            </label>
            <input
              id="password"
              type="password"
              required
              minLength={8}
              autoComplete="new-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              className="w-full bg-surface-container-low rounded-lg px-4 py-3 font-sans text-body-md text-on-surface focus:outline-none focus:ring-2 focus:ring-primary"
            />
            <p className="font-sans text-label-sm text-on-surface-variant mt-1">
              At least 8 characters.
            </p>
          </div>

          {error && (
            <p role="alert" className="font-sans text-label-md text-secondary">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={isLoading}
            className="w-full px-6 py-3 bg-primary hover:bg-primary-container text-on-primary rounded-lg font-sans text-label-lg uppercase tracking-wider transition-all shadow-md hover:shadow-xl disabled:opacity-60 disabled:cursor-not-allowed"
          >
            {isLoading ? 'Creating account…' : 'Create account'}
          </button>
        </form>

        <p className="text-center font-sans text-label-md text-on-surface-variant mt-6">
          Already have an account?{' '}
          <Link to="/login" className="text-secondary font-semibold hover:underline">
            Sign in
          </Link>
        </p>
      </div>
    </main>
  )
}
