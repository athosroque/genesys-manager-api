# Arquivo — material histórico / fora do runtime

Conteúdo **não usado** pelo app em produção. Mantido para referência e histórico
de evolução do produto. Não entra no Docker Compose nem nos Dockerfiles.

| Item | Motivo do arquivamento |
| :--- | :--- |
| `create_user.py` | CLI antiga para gerar bcrypt de senha em `users.json`. Login é magic link; o admin cria usuários via `POST /auth/users` (hash aleatório só preenche o schema). |
| `frontend-audit-legado/` | UI antiga da auditoria (`AuditTimeline`, `AuditTokens`, `auditFormat`). A Trilha atual usa `AuditView` + `UserChangesList` + `AuditSearchBar`. |

Para o dicionário vivo da Audit API, use
[`refencia_retornos/DICIONARIO-AUDITORIA.md`](../../refencia_retornos/DICIONARIO-AUDITORIA.md).
