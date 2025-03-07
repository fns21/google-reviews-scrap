# Google Reviews Scraper using Selenium

# Projetos Tomados como Inspiração

### Google Maps Scraper:
[Google Maps Scraper - GitHub](https://github.com/gaspa93/googlemaps-scraper/blob/master/googlemaps.py)

### AWS Lambda Tutorial:
[Using Selenium with Chromedriver in Python](https://www.youtube.com/watch?v=8XBkm9DD6Ic)

### Criando aplicação Serverless com AWS Lambda:
[Tutorial COMPLETO](https://www.youtube.com/watch?v=RCacN_-MKPc)

---

# Alternativas de Implementação

## 1. De forma mais crua

A solução ideal seria capturar os requests do Google e identificar os endpoints que retornam os dados das reviews.

### Prós:
- **Muito Rápido:** Ao acessar diretamente os endpoints internos, evita-se carregar a página completa ou interagir com a interface do usuário.
- **Eficaz:** Se os requests forem replicados corretamente, todas as reviews podem ser obtidas sem interação manual.

### Contras:
- **Instabilidade:** O Google frequentemente altera a estrutura dos endpoints e parâmetros, o que pode quebrar a implementação.
- **Bloqueios:** Pode haver bloqueio de IPs ou exibição de CAPTCHA devido a muitos requests.
- **Termos de Serviço:** Pode violar os termos do Google, resultando em penalidades.
- **Complexidade:** Decodificar e replicar parâmetros como "pb" é desafiador, sem documentação oficial.

---

## 2. De forma mais custosa (APIs como Outscraper ou Google Places API)

### Prós:
- **Facilidade de Uso:** API bem documentada e fácil de integrar.
- **Confiabilidade:** Lida automaticamente com bloqueios e CAPTCHAs.
- **Escalabilidade:** Coleta grandes volumes de dados eficientemente.
- **Dados Estruturados:** Retorna JSON pronto para uso.
- **Conformidade Legal:** Opera dentro dos termos de serviço do Google.

### Contras:
- **Custo:** Pode ser caro dependendo do volume de dados.
- **Dependência de Terceiros:** Sujeito a mudanças na API.
- **Limitação de Personalização:** Menos controle sobre o processo de coleta.

Ideal para uso corporativo.

---

## 3. Bot de Scroll e Scrap de Componentes (Opção Escolhida)

### Prós:
- **Controle Total:** Personalizável conforme necessidade.
- **Flexibilidade:** Adaptável a diferentes sites.
- **Baixo Custo:** Sem gastos adicionais, além da infraestrutura.
- **Simula Navegação Real:** Selenium automatiza um navegador, contornando bloqueios simples.

### Contras:
- **Complexidade:** Configurar e manter scripts pode ser trabalhoso.
- **Lentidão:** Mais lento que APIs ou requests diretos.
- **Bloqueios:** Google pode detectar e bloquear acessos repetitivos.

---

Conforme especificado, a implementação deveria ser estável, escalável e de baixo custo, por esses motivos a terceira opção foi a escolhida.

# Implementação

A principal ideia para evitar reprocessamento desnecessário é a seguinte:

1. **Primeira Execução:** O script foca primeiro em scrollar a página e carregar todas as reviews. O scraping é feito apenas no final.
2. **Execuções Posteriores:** Apenas as novas reviews são coletadas dinamicamente.

Isso é possível devido à ordenação por "Mais Recentes". Em novas execuções, o scroll ocorre até encontrar uma review já salva, evitando a coleta repetitiva e economizando tempo e recursos.

## Identificação de Reviews

- Cada review recebe um **ID único**, gerado a partir do **nome do autor, nota, tempo e comentário**.
- O ID é criado com uma função de hash (como **MD5**) para garantir unicidade.
- Antes de salvar uma review, o script verifica se o ID já está presente no arquivo JSON auxiliar.
- Se o ID já existir, a review é ignorada. Caso contrário, é adicionada ao JSON.

## Benefícios

- **Evita Duplicidade:** Garante que cada review seja coletada apenas uma vez.
- **Eficiência:** A comparação por ID é feita em **O(1)** usando uma estrutura hash.
- **Otimiza Tempo e Recursos:** Reduz carga desnecessária no sistema.

Essa abordagem garante estabilidade, escalabilidade e baixo custo, atendendo às necessidades do projeto.

