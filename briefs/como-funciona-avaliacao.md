# Como funciona a avaliação (para o aluno)

Nesta disciplina, **você entrega cada tarefa fazendo um commit**. Ao longo da aula, os cartões **"Ponto de commit"** mostram exatamente o que salvar e quando.

## Passo a passo

1. Faça a tarefa descrita logo antes do cartão.
2. No cartão **"Ponto de commit · T1"**, clique em **Copiar** e cole o comando no terminal, dentro da pasta do seu repositório. Ele é algo como:
   ```bash
   git add . && git commit -m "T1: ..." && git push
   ```
3. Pronto — esse commit registra a tarefa **T1**. Siga para o próximo ponto.

## Regras que importam

- **A mensagem começa com o código da tarefa** (`T1:`, `T2:`, …). É por ela que a correção automática identifica o que você entregou — **não altere esse prefixo**.
- **Um commit por tarefa**, na ordem. Prefira commitar cada ponto separadamente.
- **Pode refazer:** se melhorar uma tarefa, faça um novo commit com o mesmo código (`T2: ...`). Vale sempre o **mais recente**.
- **Não esqueça o `git push`** — sem enviar, seu trabalho não chega para correção.
- Uma tarefa **sem commit** correspondente vale **zero**.

## Como a nota é calculada

- A cada `push`, uma correção automática avalia **cada tarefa no estado do commit dela**. Por isso tudo bem reescrever o mesmo arquivo entre as partes: cada `Tn` é avaliado no seu próprio ponto da história.
- Cada tarefa verifica se o projeto **compila** e se cumpre os **requisitos** daquele ponto. A nota da tarefa é **proporcional** ao que passou.
- A nota final é a soma dos pontos, **normalizada de 0 a 10**.

## Dicas rápidas

- Compile/teste **antes** de commitar.
- Use **exatamente** a mensagem do cartão (o botão de copiar já traz o código certo).
- Fez os commits na ordem `T1`, `T2`, …? Ótimo — é assim que a numeração casa com a correção.
