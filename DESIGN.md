---
name: Genesys Manager Design System
description: Design tokens and UI guidelines for the Genesys Manager Platform
colors:
  brand: "#FF4F1F"
  brand-hover: "#E8461A"
  brand-soft: "#FFF1EB"
  ink: "#1A1A1A"
  canvas: "#F4F6F8"
  peach: "#FFF5F0"
  sidebar: "#EBF5FF"
  ice: "#E6F4F9"
  surface: "#FFFFFF"
  border-light: "#F0F2F5"
  border-subtle: "#E5E7EB"
  text-muted: "#6B7280"
  text-subtle: "#9CA3AF"
  accent-green: "#10B981"
  accent-green-soft: "#ECFDF5"
  accent-red: "#EF4444"
  accent-red-soft: "#FEF2F2"
  accent-amber: "#F59E0B"
  accent-amber-soft: "#FFFBEB"
typography:
  headline:
    fontFamily: Inter, system-ui, sans-serif
    fontSize: 24px
    fontWeight: 700
    lineHeight: 1.2
  title:
    fontFamily: Inter, system-ui, sans-serif
    fontSize: 16px
    fontWeight: 600
    lineHeight: 1.3
  body:
    fontFamily: Inter, system-ui, sans-serif
    fontSize: 14px
    fontWeight: 400
    lineHeight: 1.5
  caption:
    fontFamily: Inter, system-ui, sans-serif
    fontSize: 12px
    fontWeight: 500
    lineHeight: 1.4
  mono:
    fontFamily: ui-monospace, SFMono-Regular, Menlo, monospace
    fontSize: 11px
    fontWeight: 500
    lineHeight: 1.4
rounded:
  sm: 8px
  md: 12px
  lg: 16px
  xl: 24px
  full: 9999px
spacing:
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 32px
components:
  button-primary:
    backgroundColor: "{colors.brand}"
    textColor: "#FFFFFF"
    rounded: "{rounded.full}"
    padding: "10px 20px"
  card:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.xl}"
    padding: "24px"
---

# Genesys Manager Design System

## Overview
O **Genesys Manager** é uma plataforma corporativa e analítica voltada para operação, diagnóstico e auditoria de contact center na Genesys Cloud. O design prioriza legibilidade, clareza tipográfica, respostas em tempo real e separação inequívoca de status operacional.

## Colors
- **Brand (`#FF4F1F`)**: Laranja corporativo enérgico para botões primários, badges de destaque e barras de progresso ativas.
- **Ink (`#1A1A1A`)**: Tipografia principal em preto suave, proporcionando alto contraste sem agressividade visual.
- **Canvas (`#F4F6F8`)**: Fundo geral limpo, contrastando com superfícies de cartão brancas.
- **Ice / Peach / Softs**: Superfícies de apoio para chips, tabelas e estados neutros ou hover.
- **Estados Semânticos**:
  - Remoção / Erro: Vermelho (`#EF4444`) com fundo `#FEF2F2`.
  - Inativação / Advertência: Âmbar (`#F59E0B`) com fundo `#FFFBEB`.
  - Ativação / Sucesso: Verde esmeralda (`#10B981`) com fundo `#ECFDF5`.

## Typography
A família tipográfica padrão é **Inter**, complementada por monoespaçada para UUIDs, timestamps ISO-8601 e referências técnicas.

## Layout & Hierarchy
- **Cards**: Cantos arredondados generosos (`rounded-2xl` a `rounded-3xl`), bordas sutis (`border-black/[0.04]` ou `border-gray-200`) e sombras leves de elevação (`boxShadow.card`).
- **Navegação em Abas / Segmentos**: Controles em pílula arredondada (`rounded-full`) com transições suaves de cor de fundo e borda ativa.
- **Linhas do Tempo e Narrativas**: Cards em linguagem natural ("Removido da fila X por Y em Z") em vez de tabelas brutas de atributos, tornando a auditoria imediatamente inteligível para gestores e auditores.

## Do's and Don'ts
- **DO**: Usar sentenças humanas claras nos cards de auditoria, discriminando formalmente "Removido da fila" de "Inativado na fila".
- **DO**: Manter a paleta de cores estritamente alinhada aos tokens existentes.
- **DON'T**: Usar roxo não autorizado ou estilos fora da identidade visual do Genesys Manager.
- **DON'T**: Forçar o usuário a memorizar UUIDs; sempre fornecer autocomplete para filas e pessoas.
