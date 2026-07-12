// Mantido por compatibilidade — o cache de nomes de usuário agora vive em
// useEntityNames.js, junto com os caches bulk de role/group. Contrato antigo
// ({ prime, resolveMany, nameOf }) preservado; a fonte de nome mudou de
// /users/search (pesado) para /users/{id}/name (leve).
export { useUserNames } from './useEntityNames'
