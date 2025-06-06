# Planejamento de Integração com Gateway de Pagamento

Este documento descreve as considerações conceituais para a integração de um gateway de pagamento com o ERP Escolar.

## 1. Requisitos Chave para o Gateway de Pagamento

O gateway de pagamento ideal deve atender aos seguintes requisitos:

*   **Suporte a Métodos de Pagamento Essenciais:**
    *   Boleto Bancário Registrado (com API para geração e consulta).
    *   PIX (com API para geração de QR Code e consulta de status).
    *   Cartão de Crédito (com suporte a parcelamento e, idealmente, tokenização para recorrência).
*   **API Robusta e Bem Documentada:** Preferencialmente RESTful, com documentação clara e exemplos de código.
*   **Webhooks Confiáveis:** Para notificação em tempo real de status de pagamento (essencial para boletos e PIX).
*   **Operação no Brasil:** Totalmente funcional e adaptado ao mercado brasileiro.
*   **Tarifas Competitivas:** Análise de custos por transação, saques, e outras taxas.
*   **Bom Suporte Técnico:** Canais de suporte eficientes.
*   **Segurança:** Conformidade com PCI DSS para transações de cartão.
*   **Facilidade de Conciliação:** Relatórios e/ou APIs que auxiliem na conciliação financeira.

## 2. Opções de Gateway (Exemplos para Pesquisa)

Alguns gateways populares no Brasil que poderiam ser considerados (a escolha final requer pesquisa detalhada):

*   **PagSeguro (PagBank):** Ampla gama de soluções, popular no Brasil.
*   **Mercado Pago:** Forte no e-commerce, APIs conhecidas.
*   **Stripe:** Plataforma global com forte presença no Brasil, excelente para desenvolvedores, especialmente para cartões e recorrência.
*   **Pagar.me:** Focado em conversão e customização.
*   **Efí (antiga Gerencianet):** Boas soluções para boletos e PIX.
*   **Asaas:** Plataforma de automação de cobranças.

## 3. Fluxos de Integração Essenciais (Resumo)

### 3.1. Geração de Cobrança/Boleto

1.  **Criação no ERP:** Uma nova taxa (`Fee`) é criada no banco de dados do ERP.
2.  **Registro no Gateway:** O ERP faz uma chamada à API do gateway, enviando os dados da cobrança (valor, vencimento, pagador, etc.).
3.  **Retorno do Gateway:** O gateway processa o registro e retorna informações como um ID da transação no gateway, link para o boleto em PDF, e a linha digitável (código de barras).
4.  **Armazenamento no ERP:** O ERP armazena o ID do gateway e a linha digitável/link na `Fee` correspondente para exibição ao usuário.

### 3.2. Confirmação de Pagamento via Webhook

1.  **Pagamento pelo Usuário:** O pai/responsável efetua o pagamento do boleto, PIX, ou fatura do cartão.
2.  **Notificação do Gateway:** Após a confirmação do pagamento pelo sistema bancário/adquirente, o gateway envia uma notificação (evento) para um endpoint de Webhook configurado no ERP.
3.  **Processamento no ERP:**
    *   O endpoint de Webhook do ERP recebe a notificação.
    *   Valida a autenticidade da notificação (ex: usando uma assinatura secreta).
    *   Identifica a `Fee` no banco de dados do ERP usando o ID da transação fornecido pelo gateway na notificação.
    *   Cria um registro de `Payment` no ERP com os dados do pagamento (data, valor pago, método).
    *   Atualiza o status da `Fee` para "Paga" (ou "Parcialmente Paga").
    *   (Opcional) Dispara outras ações, como notificar o usuário sobre a confirmação.

## 4. Considerações de Segurança na Integração

*   **Proteção de Chaves de API:** As chaves de acesso à API do gateway devem ser armazenadas de forma segura (ex: variáveis de ambiente, secrets manager) e nunca expostas no código-fonte ou em repositórios públicos.
*   **Validação de Webhooks:** As notificações recebidas via webhook devem ser validadas para garantir que são originadas pelo gateway e não foram adulteradas. Isso geralmente é feito verificando uma assinatura digital enviada no cabeçalho da requisição do webhook.
*   **HTTPS:** Todas as comunicações com a API do gateway e o endpoint de webhook devem ser feitas sobre HTTPS.
*   **PCI Compliance:** Ao lidar com pagamentos de cartão de crédito, garantir que a integração siga as melhores práticas de segurança e, se possível, utilizar soluções de checkout (como iframes ou bibliotecas JS do gateway) que minimizem o escopo de conformidade PCI DSS para o ERP.
