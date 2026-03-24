# 🚀 Genesys Manager: Frontend Dashboard

A interface do Genesys Manager é uma Single Page Application (SPA) construída com **Vue 3** e **Vite**, focada em velocidade operacional e experiência do usuário clara para processos de gestão.

---

## 🛠️ Stack Tecnológica

- **Vue 3 (Composition API)**: Framework reativo com a sintaxe `<script setup>` para código limpo e modular.
- **Vite**: Build tool de última geração que permite HMR (Hot Module Replacement) instantâneo.
- **Tailwind CSS v4**: Framework CSS utility-first que permite a criação de interfaces customizadas com zero CSS escrito à mão.
- **Vue Router**: Motor de navegação com suporte a *Navigation Guards* para proteção de rotas.
- **Vitest**: Framework de testes unitários focado em componentes Vue.

---

## 🧠 Arquitetura de Estado e Lógica

O frontend utiliza o padrão de **Composables** para encapsular lógica de negócio reutilizável e estado global reativo:

1.  **useAuth.js**:
    - Gerencia o estado do usuário logado (`user`, `isAuthenticated`).
    - Realiza chamadas de `login` e `logout`.
    - Intercepta a inicialização do app para verificar sessões ativas via `/api/auth/me`.

2.  **useToast.js**:
    - Sistema de notificações globais.
    - Permite disparar avisos de `sucesso`, `erro` ou `loading` de qualquer parte da aplicação.

3.  **Security (Navigation Guards)**:
    - Todas as rotas (exceto `/login`) são protegidas. Se o estado `isAuthenticated` for falso, o usuário é redirecionado automaticamente para a autenticação.

---

## 🏗️ Fluxo de Produção (Docker + Nginx)

O deploy do frontend é realizado em **Multi-stage Build**:
1.  **Stage 1 (Build):** Usa uma imagem Node.js para compilar e otimizar os ativos (JS, CSS, HTML).
2.  **Stage 2 (Serve):** Os arquivos estáticos gerados são copiados para uma imagem **NGINX** leve.
3.  **NGINX Proxy:** Configurado para servir a SPA e encaminhar requisições `/api/*` para o container de backend, resolvendo problemas de CORS de forma nativa.

---

## 📁 Estrutura de Diretórios

```text
├── src/
│   ├── api/            # Abstração de chamadas HTTP (Fetch wrappers)
│   ├── views/          # Páginas principais (Login, Consulta, Migração)
│   ├── components/     # Componentes UI (Cards, Search, Modals)
│   ├── composables/    # Lógica de estado reativo (Hooks)
│   ├── router/         # Configuração de rotas e guardiões
│   └── assets/         # Imagens e estilos globais
├── public/             # Arquivos estáticos puros
└── nginx.conf          # Configuração do servidor de produção
```

---
**Design System:** O projeto utiliza uma paleta de cores harmoniosa baseada em tons de **Teal** e **Dark Slate**, otimizada para longos períodos de uso sem fadiga visual.
