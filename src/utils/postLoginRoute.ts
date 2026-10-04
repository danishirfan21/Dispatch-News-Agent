import { getProfile } from '../api/profile'
import { getLatestBrief } from '../api/brief'

/** Decides where a just-authenticated user should land, so returning users
 * never have to re-describe their interests. */
export async function resolvePostLoginRoute(): Promise<string> {
  const profile = await getProfile().catch(() => null)
  if (!profile) return '/setup'

  const brief = await getLatestBrief().catch(() => null)
  return brief ? '/brief' : '/setup'
}
