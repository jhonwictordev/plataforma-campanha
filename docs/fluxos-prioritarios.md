# Tres fluxos prioritarios

Esta demonstracao evita dispersar a avaliacao entre todos os modulos. Ela evidencia
tres jornadas completas usando exclusivamente dados sinteticos e confirma o isolamento
entre campanhas.

## Preparar a demonstracao

```bash
python manage.py migrate
python manage.py popular_dados_demo --limpar --campanhas 2 --contatos 12
python manage.py runserver
```

Todos os nomes, telefones, documentos e enderecos produzidos pelo comando sao
ficticios. Os e-mails usam `@demo.plataformacampanha.local` e a senha dos usuarios
de demonstracao e `Demo2026!`. Nao misture a base de demonstracao com uma base real.

## Fluxo 1 — criar campanha e configurar permissoes

1. Entre como `admin@demo.plataformacampanha.local`.
2. Acesse **Campanhas > Nova campanha**, preencha apenas dados ficticios e selecione
   um coordenador disponivel.
3. Entre como coordenador-geral da campanha e acesse **Usuarios > Novo usuario**.
4. Crie um mobilizador e um visualizador vinculados a essa campanha.
5. Confirme que o mobilizador pode operar o CRM e que o visualizador tem apenas leitura.

Resultado esperado: a campanha fica vinculada ao coordenador; o coordenador pode
gerenciar perfis operacionais da propria campanha, mas nao pode criar administrador.

## Fluxo 2 — cadastrar contato e acompanhar uma interacao

1. Entre como `mobilizador.1@demo.plataformacampanha.local`.
2. Acesse **CRM > Novo contato** e cadastre um personagem ficticio.
3. Abra o contato, selecione **Registrar interacao** e informe uma visita ou ligacao.
4. Volte ao detalhe e confira a interacao na linha do tempo e o contador atualizado.

Resultado esperado: contato e interacao recebem automaticamente a campanha do
usuario e nao podem referenciar responsavel ou contato de outra campanha.

## Fluxo 3 — gerar relatorio mantendo o isolamento

1. Ainda como mobilizador da campanha 1, acesse **Relatorios**.
2. Selecione **Contatos cadastrados** e gere a visualizacao ou exportacao.
3. Compare com os dados sinteticos da campanha 2 usando o administrador.
4. Tente informar manualmente o identificador da campanha 2 na URL enquanto estiver
   autenticado como mobilizador da campanha 1.

Resultado esperado: o filtro de campanha recebido do navegador e ignorado para o
usuario comum. O relatorio permanece limitado a campanha vinculada ao usuario e nao
exibe nomes, totais ou detalhes da outra campanha.

## Matriz de permissoes dos fluxos

| Perfil | Criar campanha | Gerenciar usuarios | Ler CRM | Alterar CRM/interacoes | Relatorios permitidos | Escopo |
|---|---:|---:|---:|---:|---|---|
| Administrador do sistema (`is_staff`/superuser) | Sim | Todos os perfis | Sim | Sim | Todos | Multicampanha |
| Coordenador-geral | Sim | Perfis operacionais | Sim | Sim | Todos | Campanha vinculada nos dados operacionais |
| Coordenador regional | Nao | Nao | Sim | Sim | Operacionais | Campanha vinculada |
| Financeiro | Nao | Nao | Nao | Nao | Financeiro, metas e produtividade | Campanha vinculada |
| Comunicacao | Nao | Nao | Sim | Sim | Operacionais e comunicacao | Campanha vinculada |
| Mobilizador | Nao | Nao | Sim | Sim | Operacionais | Campanha vinculada |
| Voluntario | Nao | Nao | Nao | Nao | Agenda autorizada | Campanha vinculada |
| Visualizador | Nao | Nao | Sim | Nao | Somente leitura autorizada | Campanha vinculada |

O papel funcional nunca substitui o filtro de campanha. Toda consulta operacional deve
passar pelo escopo do usuario, e IDs fornecidos pelo navegador nao ampliam esse escopo.

## Prova automatizada

```bash
python manage.py test core.tests_fluxos_prioritarios --settings=config.settings.test
```

O teste executa as tres jornadas pelas views Django reais e usa somente entidades
marcadas como `DEMO`, personagens ficticios e o dominio local reservado do projeto.
