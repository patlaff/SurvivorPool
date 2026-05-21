import { useNavigate } from 'react-router-dom'
import { GoogleLogin } from '@react-oauth/google'
import { useAuth } from '../hooks/useAuth'

export default function LoginPage() {
  const { loginWithGoogle } = useAuth()
  const navigate = useNavigate()

  return (
    <div className="min-h-screen bg-survivor-dark flex flex-col items-center justify-center gap-8 px-4">
      <div className="text-center">
        <h1 className="text-5xl font-bold text-survivor-orange mb-2">🔥 SurvivorPool</h1>
        <p className="text-gray-400 text-lg">Outwit. Outplay. Outdraft.</p>
      </div>

      <div className="bg-white/5 border border-white/10 rounded-2xl p-10 w-full max-w-sm flex flex-col items-center gap-6">
        <div className="text-center">
          <h2 className="text-white text-xl font-semibold mb-1">Sign in to play</h2>
          <p className="text-gray-500 text-sm">A Google account is required</p>
        </div>

        <GoogleLogin
          onSuccess={async (cred) => {
            if (!cred.credential) return
            await loginWithGoogle(cred.credential)
            navigate('/')
          }}
          onError={() => console.error('Google login failed')}
          theme="filled_black"
          shape="pill"
          size="large"
          text="signin_with"
        />
      </div>
    </div>
  )
}
