# Case Comercial — Plataforma de Gestão de Campanhas Políticas e Mandatos

## PROBLEMA
Coordenações de campanha eleitoral, gabinetes parlamentares e consultorias políticas enfrentam gargalos críticos durante o período pré-eleitoral e de campanha: cadastros de eleitores dispersos em planilhas do Excel sem segurança, falta de visibilidade sobre o trabalho das lideranças nos bairros, descontrole de despesas com risco de rejeição de contas pela Justiça Eleitoral e vulnerabilidade a vazamentos de dados pessoais (violação da LGPD).

## SOLUÇÃO
A **Plataforma de Campanha** é um ecossistema modular corporativo desenvolvido em Django e PostgreSQL. A solução organiza a inteligência da campanha em 16 módulos especializados, integrando mobilização de eleitores, mapa eleitoral georreferenciado, controle de agenda do candidato, metas diárias de equipes de rua, prestação de contas financeiras com auditoria detalhada e emissão de relatórios oficiais em Excel e PDF.

## FUNCIONALIDADES COMPROVADAS
- **Mapeamento Eleitoral e Gestão Territorial**: Segmentação de eleitores por zonas, seções, bairros e microrregiões com acompanhamento de metas de votação.
- **Gestão de Lideranças e Articulação**: Cadastro de articuladores locais, histórico de reuniões e monitoramento de desempenho da rede de apoio.
- **Controle Financeiro e Prestação de Contas**: Lançamento rigoroso de doações, receitas estimáveis e despesas de campanha com categorização contábil.
- **Trilha de Auditoria Integral**: Registro indelével de quem acessou, modificou ou exportou dados de eleitores, garantindo conformidade com a LGPD.
- **Mecanismos Avançados de Segurança**: Autenticação de dois fatores (2FA via QR Code/TOTP com `django-otp`) e proteção ativa contra ataques de força bruta com bloqueio de IP (`django-axes`).
- **Geração Automatizada de Relatórios**: Exportação instantânea de listas de presença, mapas de votação e demonstrativos em planilhas (`openpyxl`/`xlsxwriter`) e relatórios gráficos em PDF (`reportlab`).
- **Processamento Assíncrono com Celery & Redis**: Envio de comunicações em massa e consolidação de métricas sem travamento da interface de usuário.

## TECNOLOGIAS VERIFICADAS
- **Backend & Framework**: Python, Django 5, Django REST Framework, SimpleJWT.
- **Banco de Dados & Persistência**: PostgreSQL (driver `psycopg3`), modelo relacional robusto com migrations completas.
- **Mensageria & Filas**: Celery, Redis, Django Celery Beat.
- **Segurança & Compliance**: Django Axes, Django OTP, WhiteNoise, Gunicorn.
- **Automação & Testes**: 15 suítes de testes unitários integradas a cada submódulo (`campanhas`, `eleitores`, `equipe`, `financeiro`, `liderancas`, `metas`, etc.).

## DIFERENCIAIS
- **Amplitude Funcional Comprovada**: Mais de 330 arquivos de código estruturados em arquitetura desacoplada e testada.
- **Blindagem Jurídica e Eleitoral**: Trilha de auditoria e limites de exportação desenhados sob medida para as exigências da legislação eleitoral e LGPD.
- **Pronto para Uso Imediato**: Inclui scripts de seed, configuração para Docker Compose e manifesto para deploy gerenciado no Render.

## STATUS
**Plataforma Completa de Alta Maturidade** — Código maduro, banco relacional consolidado, regras de negócio complexas validadas e ampla cobertura de testes funcionais.

## VALOR COMERCIAL
- **Centralização da Tomada de Decisão**: Permite ao coordenador de campanha visualizar o mapa térmico de apoio e alocar recursos e carreatas onde há real potencial de votos.
- **Mitigação de Riscos Jurídicos**: Previne penalidades financeiras e cassações por meio do controle estrito do teto de gastos e rastreamento de dados de apoiadores.
- **Recorrência em Mandatos**: Pode ser comercializada tanto no ciclo eleitoral (software de campanha) quanto durante todo o mandato parlamentar (gestão de gabinete e CRM político).
