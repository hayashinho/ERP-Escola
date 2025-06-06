# Descrições Textuais dos Wireframes do Sistema de Gestão Escolar

Este documento descreve os elementos visuais e funcionais planejados para as principais telas do sistema, servindo como guia para o desenvolvimento do frontend.

## 1. Página de Login
*   (Conteúdo existente mantido)

## 2. Portal do Aluno/Pais - Dashboard Principal
*   (Conteúdo existente mantido, com as atualizações da tarefa anterior já incorporadas)
*   **Menu de Navegação Lateral (ou Superior):**
    *   Início (Dashboard)
    *   Boletim/Notas
    *   Frequência
    *   Agenda/Eventos
    *   Materiais Didáticos
    *   Minhas Finanças (Atualizado de "Financeiro (Boletos)")
    *   Comunicados
    *   Meus Dados/Perfil
*   **Seção Principal (Conteúdo do Dashboard):**
    *   (Conteúdo existente mantido)
    *   **Cartão/Widget "Situação Financeira" (para pais):**
        *   Status do próximo boleto/cobrança (a vencer, vencido).
        *   Link para "Ver Minhas Finanças".

## 3. Portal do Aluno/Pais - Visualização de Boletim
*   (Conteúdo existente mantido, com as atualizações da tarefa anterior já incorporadas)

## 4. Portal do Aluno/Pais - Minhas Finanças

**Objetivo:** Permitir que pais e alunos (se aplicável) visualizem suas cobranças, boletos e histórico de pagamentos.

*   **Título da Página:** "Minhas Finanças - [Nome do Aluno/Responsável]"
*   **Abas de Navegação:**
    *   **Aba 1: Cobranças/Boletos**
    *   **Aba 2: Histórico de Pagamentos**

*   **Subseção/Aba 1: Cobranças/Boletos**
    *   **Título:** "Minhas Cobranças e Boletos"
    *   **Filtros:**
        *   Dropdown "Status": Todos, Pendentes, Pagos, Vencidos, Cancelados.
        *   Seletor de Período "Vencimento": Intervalo de datas (De/Até) ou Mês/Ano.
    *   **Tabela de Cobranças/Boletos:**
        *   **Colunas:**
            *   Descrição (Ex: Mensalidade Março/2024, Taxa Material Didático 2024)
            *   Data de Vencimento
            *   Valor Original/Nominal (R$)
            *   Descontos (R$) (se aplicável)
            *   Multas/Juros (R$) (se aplicável)
            *   Valor Total a Pagar (R$) (calculado)
            *   Valor Pago (R$)
            *   Status (Pendente, Pago, Vencido, Cancelado, Parcialmente Pago)
            *   **Ações:**
                *   Botão/Ícone "Ver Detalhes" (leva para uma tela de detalhe da cobrança, mostrando pagamentos parciais se houver)
                *   Botão/Ícone "Gerar 2ª Via / Pagar" (se pendente/vencido, pode gerar boleto atualizado ou link para gateway)
                *   (Para pagos) Botão/Ícone "Ver Comprovante" (se disponível)
    *   **Resumo (Opcional):** Valor total pendente, valor total vencido.

*   **Subseção/Aba 2: Histórico de Pagamentos**
    *   **Título:** "Meu Histórico de Pagamentos"
    *   **Filtros:**
        *   Seletor de Período "Data do Pagamento": Intervalo de datas (De/Até) ou Mês/Ano.
        *   Dropdown "Método de Pagamento": Todos, Boleto, Cartão de Crédito, PIX, etc.
    *   **Tabela de Pagamentos:**
        *   **Colunas:**
            *   Data do Pagamento
            *   Descrição da Cobrança Paga (Ex: Mensalidade Março/2024)
            *   Valor Pago (R$)
            *   Método de Pagamento
            *   ID da Transação (se aplicável, ex: ID do gateway, NSU)
            *   **Ações:**
                *   Botão/Ícone "Ver Detalhes do Pagamento" (mostra mais detalhes, se houver, ou link para o detalhe da cobrança associada)
                *   (Opcional) Botão/Ícone "Baixar Comprovante"

## 5. Formulário de Pré-Cadastro de Aluno (Pais)
*   (Conteúdo existente mantido, com as atualizações da tarefa anterior já incorporadas)

## 6. Painel da Secretaria - Validação de Cadastro de Aluno
*   (Conteúdo existente mantido)

### 6.1. Tela 1: Lista de Cadastros Pendentes
*   (Conteúdo existente mantido)

### 6.2. Tela 2: Detalhes do Cadastro Pendente
*   (Conteúdo existente mantido)

## 7. Portal do Aluno/Pais - Consulta à Frequência
*   (Conteúdo existente mantido)

## 8. Portal do Aluno/Pais - Agenda Virtual
*   (Conteúdo existente mantido)

## 9. Portal do Aluno/Pais - Materiais Didáticos
*   (Conteúdo existente mantido)

## 10. Painel Administrativo - Professor
*   (Conteúdo existente mantido, com as atualizações da tarefa anterior já incorporadas)

### 10.1. Dashboard do Professor
*   (Conteúdo existente mantido)
### 10.2. Minhas Atribuições (Turmas/Disciplinas)
*   (Conteúdo existente mantido)
### 10.3. Tela de Lançamento de Notas
*   (Conteúdo existente mantido)
### 10.4. Tela de Lançamento de Frequência
*   (Conteúdo existente mantido)
### 10.5. Formulário de Criação/Edição de Eventos na Agenda
*   (Conteúdo existente mantido)
### 10.6. Upload e Gerenciamento de Materiais Didáticos
*   (Conteúdo existente mantido)

---
## 11. Painel da Secretaria - Gestão Financeira

**Objetivo:** Permitir que a equipe da secretaria gerencie todas as aspects financeiros, incluindo a criação e acompanhamento de cobranças, registro de pagamentos e relatórios.

*   **Sub-itens de Menu (no painel da secretaria):**
    *   Gerenciar Cobranças/Taxas
    *   Registrar Pagamento Manual
    *   Consultar Pagamentos Recebidos
    *   Relatório de Inadimplência
    *   (Opcional) Configurações Financeiras (planos, descontos, multas)

### 11.1. Tela: Gerenciar Cobranças/Taxas (Fees)

*   **Título da Página:** "Gerenciamento de Cobranças e Taxas"
*   **Ação Principal:** Botão "+ Nova Cobrança" (abre o formulário de criação).
*   **Filtros Avançados:**
    *   Busca: Nome do Aluno, CPF do Aluno, Descrição da Cobrança, ID do Gateway.
    *   Dropdown "Ano Letivo".
    *   Dropdown "Série/Nível".
    *   Dropdown "Turma".
    *   Dropdown "Status da Cobrança" (Pendente, Pago, Vencido, etc.).
    *   Seletor de Período "Data de Vencimento" (De/Até).
    *   Botão "Aplicar Filtros", Botão "Limpar Filtros".
*   **Tabela de Cobranças:**
    *   **Colunas:**
        *   Aluno (Nome Completo)
        *   Descrição da Cobrança
        *   Data de Vencimento
        *   Valor Original (R$)
        *   Valor Total (com descontos/multas, R$)
        *   Valor Pago (R$)
        *   Status
        *   Ano Letivo
        *   (Opcional) Turma
        *   **Ações por Item:**
            *   Botão/Ícone "Editar Cobrança" (abre formulário de edição).
            *   Botão/Ícone "Ver Detalhes" (abre tela de detalhes da cobrança).
            *   Botão/Ícone "Excluir Cobrança" (com confirmação, apenas se não houver pagamentos).
            *   Botão/Ícone "Gerar 2ª Via / Link de Pagamento".
            *   Botão/Ícone "Registrar Pagamento" (atalho para 11.2 com a taxa pré-selecionada).
    *   **Paginação.**
    *   **(Opcional) Ações em Lote:** Checkbox para selecionar múltiplas cobranças e aplicar ações (Ex: Enviar Lembrete, Cancelar em Lote).

*   **Sub-Tela/Modal: Formulário de Criação/Edição de Cobrança (`FeeWriteSerializer`)**
    *   **Título:** "Nova Cobrança" ou "Editar Cobrança: [Descrição]"
    *   **Campos:**
        *   Dropdown/Autocomplete "Aluno (`student`)": Selecionar o aluno.
        *   Dropdown "Ano Letivo (`school_year`)": Selecionar o ano letivo.
        *   Campo "Descrição (`description`)": Input de texto.
        *   Campo "Data de Vencimento (`due_date`)": Seletor de data.
        *   Campo "Valor Original (`amount`)": Input numérico (decimal).
        *   Dropdown "Status (`status`)": Pendente, Pago, Vencido, Cancelado, etc. (Secretaria pode definir manualmente).
        *   Campo "ID do Gateway de Pagamento (`payment_gateway_id`)": Input de texto, opcional.
        *   Campo "Código de Barras (`barcode`)": Input de texto, opcional.
        *   Campo "Valor do Desconto (`discount_amount`)": Input numérico, default 0.
        *   Campo "Valor da Multa (`penalty_amount`)": Input numérico, default 0.
        *   Campo "Valor Já Pago (`amount_paid`)": Input numérico, default 0 (para casos de registro retroativo ou ajuste).
        *   Campo "Data do Último Pagamento (`payment_date`)": Seletor de data (se `amount_paid` > 0).
        *   Área de Texto "Observações Internas (`notes`)".
        *   (Se editando) Área de Texto "Motivo da Edição (`edit_reason`)": Obrigatório se campos financeiros chave (valor, vencimento, status) forem alterados.
    *   **Botões:** "Salvar Cobrança", "Cancelar".

*   **Sub-Tela/Modal: Detalhes da Cobrança (`FeeSerializer` com informações de `FeeEditLog` e `Payment`)**
    *   **Título:** "Detalhes da Cobrança: [Descrição] - Aluno: [Nome Aluno]"
    *   **Seção 1: Informações da Cobrança:** Exibição de todos os campos da cobrança (descrição, aluno, ano letivo, vencimento, valor original, descontos, multas, valor total, valor pago, status, ID gateway, código de barras, notas).
    *   **Seção 2: Pagamentos Recebidos para esta Cobrança:**
        *   Tabela/Lista de pagamentos (Data Pagamento, Valor Pago, Método, ID Transação, Confirmado Por, Ações: "Ver Detalhes do Pagamento").
        *   Botão "+ Registrar Novo Pagamento para esta Cobrança".
    *   **Seção 3: Histórico de Edições desta Cobrança:**
        *   Tabela/Lista de logs de edição (Data/Hora, Campo Alterado, Valor Anterior, Novo Valor, Usuário Editor, Motivo).
    *   **Botões de Ação:** "Editar Cobrança", "Gerar 2ª Via", "Voltar para Lista".

### 11.2. Tela: Registrar Pagamento Manual

*   **Título da Página:** "Registrar Pagamento Manual"
*   **Formulário de Registro de Pagamento (`PaymentWriteSerializer`):**
    *   Dropdown/Autocomplete "Cobrança/Taxa (`fee`)": Selecionar a cobrança que está sendo paga. Ao selecionar, exibe detalhes da cobrança (aluno, descrição, valor pendente).
    *   Campo "Data do Pagamento (`payment_date`)": Seletor de data, default para data atual.
    *   Campo "Valor Pago (`amount_paid`)": Input numérico (decimal).
    *   Dropdown "Método de Pagamento (`payment_method`)": Boleto, Cartão, PIX, Dinheiro, etc.
    *   Campo "ID da Transação/Referência (`transaction_id`)": Input de texto, opcional.
    *   Área de Texto "Observações do Pagamento (`notes`)": Opcional.
    *   (O campo `confirmed_by` é preenchido automaticamente com o usuário logado).
*   **Botão "Registrar Pagamento".**
*   **Feedback:** Mensagem de sucesso com link para ver o pagamento ou a cobrança atualizada.

### 11.3. Tela: Consultar Pagamentos Recebidos

*   **Título da Página:** "Consulta de Pagamentos Recebidos"
*   **Filtros Avançados:**
    *   Busca: Nome do Aluno, CPF do Aluno, Descrição da Cobrança, ID da Transação.
    *   Seletor de Período "Data do Pagamento" (De/Até).
    *   Dropdown "Método de Pagamento".
    *   Dropdown "Usuário Confirmador" (quem registrou/confirmou o pagamento).
    *   Dropdown "Ano Letivo" (da cobrança associada).
    *   Botão "Aplicar Filtros", Botão "Limpar Filtros".
*   **Tabela de Pagamentos:**
    *   **Colunas:**
        *   Data do Pagamento
        *   Aluno
        *   Descrição da Cobrança
        *   Valor Pago (R$)
        *   Método de Pagamento
        *   ID da Transação
        *   Confirmado Por (Usuário)
        *   Data da Confirmação (Registro do Pagamento)
        *   **Ações:** Botão/Ícone "Ver Detalhes do Pagamento" (mostra todos os campos do pagamento e link para a cobrança).
    *   **Paginação.**
    *   **(Opcional) Botão "Exportar Relatório" (CSV, Excel).**

### 11.4. Tela: Relatório de Inadimplência

*   **Título da Página:** "Relatório de Inadimplência"
*   **Filtros:**
    *   Dropdown "Ano Letivo".
    *   Dropdown "Série/Nível".
    *   Dropdown "Turma".
    *   Seletor de Data "Vencidas até": Para considerar cobranças vencidas até uma data específica.
    *   (Opcional) Checkbox "Apenas com status Pendente/Vencido".
    *   Botão "Gerar Relatório".
*   **Tabela de Cobranças Vencidas/Não Pagas:**
    *   **Colunas:**
        *   Aluno (Nome Completo)
        *   Contato do Responsável Principal (Telefone, Email)
        *   Descrição da Cobrança
        *   Data de Vencimento
        *   Dias em Atraso (calculado)
        *   Valor Original (R$)
        *   Multa/Juros (R$) (calculado ou registrado)
        *   Valor Devido Total (R$)
        *   Status da Cobrança
        *   (Opcional) Último Contato/Observação da Secretaria
    *   **Paginação.**
*   **Ações:**
    *   Botão "Exportar Relatório" (CSV, Excel).
    *   (Opcional) Ações em lote: Enviar email de lembrete/cobrança.

---
*Estes wireframes são descrições textuais e devem ser usados como base para a criação de protótipos visuais e desenvolvimento frontend.*
