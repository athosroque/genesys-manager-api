import { createRouter, createWebHistory } from 'vue-router'

const routes = [
    {
        path: '/',
        name: 'Home',
        component: () => import('../views/ConsultaView.vue')
    },
    {
        path: '/login',
        name: 'Login',
        component: () => import('../views/LoginView.vue')
    }
]

import { useAuth } from '../composables/useAuth'

const router = createRouter({
    history: createWebHistory(),
    routes
})

router.beforeEach(async (to) => {
    const { user, isAuthenticated, checkAuth } = useAuth()

    // Se o user ainda não foi carregado (primeiro acesso)
    if (user.value === null) {
        await checkAuth()
    }

    // Proteção de Rota: se não logado e for pra rota que não seja o login
    if (!isAuthenticated.value && to.name !== 'Login') {
        return { name: 'Login' }
    }

    // Se já estiver logado e for pro login, vai pra home
    if (isAuthenticated.value && to.name === 'Login') {
        return { name: 'Home' }
    }
})

export default router
