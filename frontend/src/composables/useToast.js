import { ref } from 'vue'

const toasts = ref([])
let toastId = 0

export function useToast() {
    const addToast = (message, type = 'info') => {
        const id = toastId++
        toasts.value.push({ id, message, type })

        // Auto remove após 5 segundos
        setTimeout(() => {
            removeToast(id)
        }, 5000)
    }

    const removeToast = (id) => {
        toasts.value = toasts.value.filter(toast => toast.id !== id)
    }

    return {
        toasts,
        addToast,
        removeToast
    }
}
