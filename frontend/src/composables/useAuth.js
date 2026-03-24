import { ref, computed } from 'vue'
import { getMe, logout as apiLogout } from '../api/auth'
import { useRouter } from 'vue-router'

// Singleton state
const user = ref(null)
const loading = ref(true) // Começa em loading para o check inicial

export function useAuth() {
    const router = useRouter()
    const isAuthenticated = computed(() => user.value !== null)

    async function checkAuth() {
        loading.value = true
        try {
            const userData = await getMe()
            user.value = userData
        } catch (err) {
            user.value = null
            // Se não estiver logado, o 401 é esperado
        } finally {
            loading.value = false
        }
    }

    async function logout() {
        try {
            await apiLogout()
        } catch (err) {
            console.error('Erro ao deslogar:', err)
        } finally {
            user.value = null
            if (router) router.push('/login')
        }
    }

    return {
        user,
        isAuthenticated,
        loading,
        checkAuth,
        logout
    }
}
