export type User = {
  id: string
  email: string
}

export class AuthError extends Error {}

async function handle(response: Response): Promise<User> {
  if (!response.ok) {
    const message = await response
      .json()
      .then((body) => (typeof body?.detail === 'string' ? body.detail : null))
      .catch(() => null)
    throw new AuthError(message ?? 'Something went wrong. Please try again.')
  }
  return (await response.json()) as User
}

export async function register(email: string, password: string): Promise<User> {
  let response: Response
  try {
    response = await fetch('/api/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ email, password }),
    })
  } catch {
    throw new AuthError("Couldn't reach the server. Check your connection and try again.")
  }
  return handle(response)
}

export async function login(email: string, password: string): Promise<User> {
  let response: Response
  try {
    response = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ email, password }),
    })
  } catch {
    throw new AuthError("Couldn't reach the server. Check your connection and try again.")
  }
  return handle(response)
}

export async function logout(): Promise<void> {
  await fetch('/api/auth/logout', { method: 'POST', credentials: 'include' }).catch(() => undefined)
}

export async function getCurrentUser(): Promise<User | null> {
  const response = await fetch('/api/auth/me', { credentials: 'include' }).catch(() => null)
  if (!response || !response.ok) return null
  return (await response.json()) as User
}
