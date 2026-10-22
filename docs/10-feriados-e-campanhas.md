# 10 — Feriados e campanhas (calendário de eventos)

Feriados, campanhas de cobrança, falhas de serviço: dias assim mudam o volume de chamadas, e o histórico sozinho não
avisa o modelo de que o próximo feriado está chegando. O **calendário de eventos** deixa você informar esses dias.
Este recurso é **opcional**: sem calendário, tudo funciona como antes.

## O arquivo do calendário

Um CSV com um evento por linha. Os nomes das colunas podem ser em português ou em inglês.

| Coluna | Para que serve |
|---|---|
| `data` (ou `date`) | Primeiro dia do evento: `2024-03-29` ou `29/03/2024` |
| `fim` (ou `end`) | Último dia, opcional. Sem ele, o evento dura só o dia da `data` |
| `tipo` (ou `type`) | O tipo do evento, em texto livre: `feriado`, `campanha`, `incidente`... |
| `efeito` (ou `effect`) | Opcional: quanto o volume muda em relação ao normal, como multiplicador. `1.5` = 50% a mais; `0.3` = 70% a menos; vazio = só marca o dia |
| `nome` (ou `name`) | Opcional: uma descrição para você |

Exemplo (`data/samples/eventos/eventos_exemplo.csv`):

```
data,fim,tipo,efeito,nome
2024-03-18,2024-03-20,campanha,1.5,Campanha de cobrança
2024-03-29,,feriado,0.3,Sexta-feira Santa
2024-05-24,2024-05-25,campanha,1.5,Campanha de fim de mês
```

Erros no arquivo (data inválida, fim antes do início, efeito que não é número ou é negativo, tipo em branco) aparecem
com uma mensagem dizendo qual é o problema.

## Duas maneiras de usar os eventos

Com um calendário carregado, a interface pergunta **como usar os eventos na previsão**:

### Ajuste pelo efeito informado (padrão)

O laboratório faz o que um planejador faria à mão:

1. **Limpa o histórico:** divide cada dia de evento pelo efeito informado, para que a campanha de março não pareça
   um dia normal para o modelo.
2. **Prevê o volume "normal"** com o TimesFM.
3. **Reaplica o efeito** nos dias de evento do futuro: multiplica a previsão (e a faixa de 10% a 90%) pelo efeito.

Só funciona com eventos que têm `efeito` maior que zero. Quem decide o tamanho do efeito é **você**: o ajuste só vale
tanto quanto a sua estimativa.

### Covariáveis do modelo

O TimesFM recebe os eventos como entrada extra, uma série por tipo de evento (valor: o efeito menos 1, por exemplo
+0,5 numa campanha de 1,5, ou −0,7 num feriado de 0,3; vale 1 quando o evento não tem efeito), e decide sozinho como
usá-los. Nada é aplicado à mão.

## Qual funciona melhor? O que os testes mostraram

O teste de realidade, com um calendário carregado, compara os dois com a previsão **sem eventos**. Nos dados de
exemplo (`chamadas_sinteticas_eventos.csv`, 12 semanas com dois feriados e três campanhas, a última nos dois dias
finais) e com o TimesFM 3.0 de verdade:

| Horizonte escondido | Sem eventos | Covariáveis do modelo | Ajuste pelo efeito |
|---|---|---|---|
| 48 intervalos (1 dia) | WAPE 18,7% | 17,7% | **14,4%** |
| 96 intervalos (2 dias, com campanha) | WAPE 35,4% (viés −34,8%) | 35,9% (viés −34,8%) | **9,2%** (viés −0,3%) |
| 144 intervalos (3 dias) | WAPE 25,5% | 25,5% | **11,5%** |

O que ler disso, com honestidade:

- As **covariáveis do modelo quase não mudaram a previsão** neste teste: com poucos eventos no histórico (três
  campanhas, dois feriados), o TimesFM 3.0 não aprendeu o efeito. Testei outras codificações (0/1, sem escala,
  normalizada, só o passado) e o resultado foi o mesmo. Com um histórico bem mais longo, com muitos eventos, ele pode
  se sair melhor: confira com o seu próprio teste de realidade.
- O **ajuste pelo efeito informado** melhorou muito, mas **nestes dados o efeito informado é exatamente o efeito
  real** (os dados foram gerados assim). Com dados reais, o seu palpite sobre o efeito terá erro, e o ganho será
  menor. Use o teste de realidade para ver quanto vale no seu caso, e ajuste o `efeito` com o que aprender.
- Por isso o **padrão é o ajuste**, mas a tela mostra os dois lado a lado: não é preciso confiar em nenhum deles
  sem olhar a comparação.

## Na interface

1. Na barra lateral, em **4. Eventos: feriados e campanhas (opcional)**, envie o seu CSV ou escolha o exemplo. A
   tabela mostra como o calendário foi lido.
2. Na aba **Previsão**, escolha **como usar os eventos** e clique em **Prever**. A mesma escolha vale no
   **Dimensionamento**.
3. Na aba **Teste de realidade**, depois do teste normal aparece **Com e sem eventos**: uma tabela com WAPE, viés,
   MAE e cobertura dos três métodos, um aviso dizendo se melhorou ou piorou e o gráfico dos três contra o real.

## Para estudar

- Mude o `efeito` da campanha de 1,5 para 1,2 no arquivo (como se você tivesse subestimado): o ajuste ainda ajuda?
- Remova as campanhas do passado e deixe só a do fim: o que acontece com as covariáveis?
- Carregue o calendário e olhe o teste de realidade de um período **sem** eventos: nada deve piorar.

## Limites

- O calendário é por **dia** (não por hora): o efeito vale para todos os intervalos do dia.
- O ajuste supõe que o efeito é um multiplicador igual ao longo do dia.
- Eventos que mudam o **TMA** (por exemplo, uma falha que deixa as ligações mais longas) não são tratados aqui.
- É um laboratório de estudo: valide antes de usar na operação.
