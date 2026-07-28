import random
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from agenda.models import EventoAgenda
from auditoria.models import LogSeguranca, PoliticaRetencaoDados, RegistroAuditoria, SolicitacaoTitularDados
from campanhas.models import Campanha
from comunicacao.models import CampanhaComunicacao, CanalComunicacao, EnvioComunicacao, ListaBloqueio, ModeloMensagem
from eleitores.models import ContatoCRM, InteracaoContato, TarefaContato
from equipe.models import IntegranteEquipe, TarefaEquipe
from financeiro.models import CategoriaFinanceira, CentroCusto, LancamentoFinanceiro, ParceiroFinanceiro
from liderancas.models import InteracaoLideranca, Lideranca
from metas.models import MetaCampanha
from usuarios.models import Usuario


@dataclass
class DemoSeedOptions:
    campanhas: int = 2
    contatos: int = 12
    liderancas: int = 6
    eventos: int = 4
    integrantes: int = 5
    tarefas: int = 8
    metas: int = 4
    lancamentos: int = 8
    comunicacoes: int = 2
    seed: int = 2026
    limpar: bool = False


class DemoSeedService:
    MUNICIPIOS = [
        ("Fortaleza", ["Aldeota", "Meireles", "Benfica", "Montese", "Parangaba"]),
        ("Caucaia", ["Centro", "Jurema", "Tabapuazinho", "Icarai", "Guajiru"]),
        ("Maracanau", ["Centro", "Jereissati I", "Jardim Jatoba", "Acaracuzinho", "Novo Maracanau"]),
        ("Juazeiro do Norte", ["Centro", "Lagoa Seca", "Salesianos", "Triangulo", "Piraja"]),
    ]
    NOMES = [
        "Ana", "Bruno", "Caio", "Daniela", "Eduarda", "Felipe", "Gabriela", "Helena",
        "Igor", "Juliana", "Karen", "Lucas", "Marina", "Nicolas", "Olivia", "Paulo",
        "Renata", "Samuel", "Talita", "Vitor", "Yasmin",
    ]
    SOBRENOMES = [
        "Almeida", "Barbosa", "Cardoso", "Dantas", "Esteves", "Ferreira", "Gomes",
        "Henrique", "Lima", "Medeiros", "Nogueira", "Pereira", "Queiroz", "Ribeiro", "Soares",
    ]
    FUNCOES_EQUIPE = [
        "Coordenacao territorial",
        "Mobilizacao de rua",
        "Comunicao comunitaria",
        "Operacao digital",
        "Logistica de agenda",
        "Relacao com apoiadores",
    ]
    DEPARTAMENTOS = ["Coordenacao", "Mobilizacao", "Comunicacao", "Financeiro", "Logistica"]

    def __init__(self, opcoes: DemoSeedOptions):
        self.opcoes = opcoes
        self.random = random.Random(opcoes.seed)
        self.agora = timezone.now()
        self.hoje = timezone.localdate()
        self.resumo = {
            "campanhas": 0,
            "usuarios": 0,
            "liderancas": 0,
            "contatos": 0,
            "eventos": 0,
            "integrantes": 0,
            "tarefas": 0,
            "metas": 0,
            "lancamentos": 0,
            "campanhas_comunicacao": 0,
            "registros_auditoria": 0,
            "logs_seguranca": 0,
        }

    @transaction.atomic
    def executar(self) -> dict[str, int]:
        if self.opcoes.limpar:
            self._limpar_dados_demo()

        admin = self._criar_admin_global()
        self.resumo["usuarios"] += 1 if admin else 0

        campanhas = self._criar_campanhas()
        self.resumo["campanhas"] = len(campanhas)

        for indice, campanha in enumerate(campanhas):
            usuarios = self._criar_usuarios_campanha(campanha, indice)
            self.resumo["usuarios"] += len(usuarios)
            campanha.coordenador_responsavel = usuarios["coordenador_geral"]
            campanha.save(update_fields=["coordenador_responsavel", "atualizado_em"])

            liderancas = self._criar_liderancas(campanha, usuarios, indice)
            contatos = self._criar_contatos(campanha, usuarios, liderancas, indice)
            eventos = self._criar_eventos(campanha, usuarios, liderancas, indice)
            integrantes = self._criar_integrantes(campanha, usuarios, indice)

            self._criar_tarefas_equipe(campanha, integrantes, indice)
            self._criar_metas(campanha, usuarios, integrantes, indice)
            self._criar_financeiro(campanha, usuarios, indice)
            self._criar_comunicacao(campanha, usuarios, contatos, indice)
            self._criar_governanca(campanha, usuarios, contatos, indice)

            self.resumo["liderancas"] += len(liderancas)
            self.resumo["contatos"] += len(contatos)
            self.resumo["eventos"] += len(eventos)
            self.resumo["integrantes"] += len(integrantes)

        return self.resumo

    def _limpar_dados_demo(self):
        campanhas_demo = list(
            Campanha.todos_objetos.filter(nome_campanha__startswith="DEMO ")
            .values_list("id", flat=True)
        )
        if campanhas_demo:
            RegistroAuditoria.todos_objetos.filter(campanha_id__in=campanhas_demo).delete()
            LogSeguranca.todos_objetos.filter(campanha_id__in=campanhas_demo).delete()
            Campanha.todos_objetos.filter(id__in=campanhas_demo).delete()
        Usuario.objects.filter(email__endswith="@demo.plataformacampanha.local").delete()

    def _criar_admin_global(self) -> Usuario:
        admin, _ = Usuario.objects.update_or_create(
            email="admin@demo.plataformacampanha.local",
            defaults={
                "nome_completo": "Administrador Demo",
                "nome_exibicao": "Admin Demo",
                "nivel_acesso": Usuario.NiveisAcesso.ADMINISTRADOR,
                "is_staff": True,
                "is_superuser": True,
                "is_active": True,
                "campanha": None,
                "telefone": "85990000001",
                "consentimento_privacidade": True,
                "data_consentimento_privacidade": self.agora,
            },
        )
        admin.set_password("Demo2026!")
        admin.save(update_fields=["password", "atualizado_em"])
        return admin

    def _criar_campanhas(self) -> list[Campanha]:
        campanhas = []
        for indice in range(self.opcoes.campanhas):
            municipio, _ = self.MUNICIPIOS[indice % len(self.MUNICIPIOS)]
            campanha, _ = Campanha.todos_objetos.update_or_create(
                numero_candidato=str(1200 + indice),
                data_eleicao=date(2026, 10, 4),
                municipio=municipio,
                defaults={
                    "nome_campanha": f"DEMO {municipio} 2026",
                    "nome_candidato": f"{self._nome_pessoa(indice)} da Esperanca",
                    "cargo_disputado": Campanha.Cargos.VEREADOR if indice % 2 == 0 else Campanha.Cargos.PREFEITO,
                    "partido": "PART",
                    "estado": "CE",
                    "data_inicio": date(2026, 7, 1) + timedelta(days=indice * 5),
                    "situacao": Campanha.Situacoes.ATIVA,
                    "cor_primaria": "#0B3C5D",
                    "cor_secundaria": "#E67E22",
                    "descricao": f"Campanha demonstrativa para operacao eleitoral em {municipio}.",
                    "objetivos_gerais": (
                        "Organizar liderancas, acompanhar metas, testar CRM e demonstrar operacao "
                        "territorial com dados ficticios."
                    ),
                },
            )
            campanhas.append(campanha)
        return campanhas

    def _criar_usuarios_campanha(self, campanha: Campanha, indice_campanha: int) -> dict[str, Usuario]:
        papeis = [
            Usuario.NiveisAcesso.COORDENADOR_GERAL,
            Usuario.NiveisAcesso.COORDENADOR_REGIONAL,
            Usuario.NiveisAcesso.FINANCEIRO,
            Usuario.NiveisAcesso.COMUNICACAO,
            Usuario.NiveisAcesso.MOBILIZADOR,
            Usuario.NiveisAcesso.VOLUNTARIO,
            Usuario.NiveisAcesso.VISUALIZADOR,
        ]
        usuarios = {}
        for indice_papel, papel in enumerate(papeis):
            usuario, _ = Usuario.objects.update_or_create(
                email=f"{papel}.{indice_campanha + 1}@demo.plataformacampanha.local",
                defaults={
                    "nome_completo": f"{self._nome_pessoa(indice_campanha + indice_papel + 3)} {papel.replace('_', ' ').title()}",
                    "nome_exibicao": papel.replace("_", " ").title(),
                    "telefone": self._telefone("85", indice_campanha, indice_papel, base=91),
                    "campanha": campanha,
                    "nivel_acesso": papel,
                    "is_active": True,
                    "consentimento_privacidade": True,
                    "data_consentimento_privacidade": self.agora,
                    "tema_escuro": papel in {
                        Usuario.NiveisAcesso.COORDENADOR_GERAL,
                        Usuario.NiveisAcesso.COMUNICACAO,
                    },
                },
            )
            usuario.set_password("Demo2026!")
            usuario.save(update_fields=["password", "atualizado_em"])
            usuarios[papel] = usuario
        return usuarios

    def _criar_liderancas(
        self,
        campanha: Campanha,
        usuarios: dict[str, Usuario],
        indice_campanha: int,
    ) -> list[Lideranca]:
        municipio, bairros = self.MUNICIPIOS[indice_campanha % len(self.MUNICIPIOS)]
        liderancas = []
        tipos = list(Lideranca.Tipos.values)
        situacoes = list(Lideranca.Situacoes.values)
        niveis = list(Lideranca.NiveisInfluencia.values)

        for indice in range(self.opcoes.liderancas):
            telefone = self._telefone("85", indice_campanha, indice, base=97)
            lideranca, _ = Lideranca.todos_objetos.get_or_create(
                campanha=campanha,
                telefone=telefone,
                defaults={
                    "nome_completo": f"{self._nome_pessoa(indice_campanha + indice + 10)} {self._sobrenome(indice)}",
                    "nome_conhecido": f"Lider {indice + 1} {municipio}",
                    "cpf": f"000.000.{indice_campanha:03d}-{indice:02d}",
                    "whatsapp": telefone,
                    "email": f"lideranca-{indice_campanha + 1}-{indice + 1}@demo.plataformacampanha.local",
                    "data_nascimento": date(1980 + (indice % 12), (indice % 12) + 1, min((indice % 27) + 1, 28)),
                    "genero": "Nao informado",
                    "tipo_lideranca": tipos[indice % len(tipos)],
                    "organizacao": f"Rede Comunitaria {bairro_ou_padrao(bairros, indice)}",
                    "cargo_funcao": "Referencia territorial",
                    "estado": "CE",
                    "cidade": municipio,
                    "bairro": bairro_ou_padrao(bairros, indice),
                    "endereco": f"Rua Demo {indice + 10}, {bairro_ou_padrao(bairros, indice)}",
                    "regiao_eleitoral": f"Regional {indice_campanha + 1}",
                    "zona_eleitoral": str(110 + indice_campanha),
                    "secao_eleitoral": str(200 + indice),
                    "apoiadores_estimados": 20 + indice * 8,
                    "nivel_influencia": niveis[indice % len(niveis)],
                    "responsavel_contato": usuarios[Usuario.NiveisAcesso.COORDENADOR_REGIONAL],
                    "situacao_relacionamento": situacoes[indice % len(situacoes)],
                    "data_ultimo_contato": self.agora - timedelta(days=indice + 2),
                    "proxima_acao": "Agendar nova rodada de alinhamento territorial",
                    "observacoes": "Registro demonstrativo para uso interno e treinamento.",
                    "tags": ["territorio", "demo", f"regional-{indice_campanha + 1}"],
                    "consentimento_dados": indice % 4 != 0,
                    "data_consentimento": self.agora - timedelta(days=20 + indice) if indice % 4 != 0 else None,
                    "latitude": Decimal(f"{-3.72 + indice_campanha * 0.01 + indice * 0.001:.6f}"),
                    "longitude": Decimal(f"{-38.54 + indice_campanha * 0.01 + indice * 0.001:.6f}"),
                },
            )
            InteracaoLideranca.todos_objetos.get_or_create(
                campanha=campanha,
                lideranca=lideranca,
                tipo=InteracaoLideranca.Tipos.REUNIAO,
                data_hora=self.agora - timedelta(days=indice + 1),
                defaults={
                    "resumo": "Reuniao inicial de apresentacao",
                    "detalhes": "Conversa simulada sobre agenda, influencia local e demandas do territorio.",
                    "responsavel": usuarios[Usuario.NiveisAcesso.MOBILIZADOR],
                },
            )
            liderancas.append(lideranca)
        return liderancas

    def _criar_contatos(
        self,
        campanha: Campanha,
        usuarios: dict[str, Usuario],
        liderancas: list[Lideranca],
        indice_campanha: int,
    ) -> list[ContatoCRM]:
        municipio, bairros = self.MUNICIPIOS[indice_campanha % len(self.MUNICIPIOS)]
        contatos = []
        etapas = list(ContatoCRM.EtapasFunil.values)

        for indice in range(self.opcoes.contatos):
            telefone = self._telefone("85", indice_campanha, indice, base=88)
            consentimento = indice % 3 != 0
            contato, _ = ContatoCRM.todos_objetos.get_or_create(
                campanha=campanha,
                telefone=telefone,
                defaults={
                    "nome_completo": f"{self._nome_pessoa(indice_campanha + indice + 30)} {self._sobrenome(indice + 3)}",
                    "whatsapp": telefone,
                    "email": f"contato-{indice_campanha + 1}-{indice + 1}@demo.plataformacampanha.local",
                    "data_nascimento": date(1990 + (indice % 10), ((indice + 2) % 12) + 1, min((indice % 27) + 1, 28)),
                    "cidade": municipio,
                    "bairro": bairro_ou_padrao(bairros, indice),
                    "endereco": f"Avenida Exemplo {indice + 100}",
                    "zona_eleitoral": str(120 + indice_campanha),
                    "secao_eleitoral": str(300 + indice),
                    "origem_contato": "Mutirao territorial demo",
                    "responsavel_cadastro": usuarios[Usuario.NiveisAcesso.MOBILIZADOR],
                    "lideranca_relacionada": liderancas[indice % len(liderancas)] if liderancas else None,
                    "status_funil": etapas[indice % len(etapas)],
                    "tags": ["crm", "demo", bairro_ou_padrao(bairros, indice).lower().replace(" ", "-")],
                    "observacoes": "Contato ficticio criado para demonstracao do funil de relacionamento.",
                    "data_primeiro_contato": self.agora - timedelta(days=30 + indice),
                    "data_ultimo_contato": self.agora - timedelta(days=indice),
                    "proxima_acao": "Retornar com proposta de participacao em agenda local",
                    "consentimento_comunicacao": consentimento,
                    "canal_autorizado": CanalComunicacao.WHATSAPP if consentimento else "",
                    "data_consentimento": self.agora - timedelta(days=10 + indice) if consentimento else None,
                    "possivel_duplicado": indice == self.opcoes.contatos - 1,
                    "latitude": Decimal(f"{-3.71 + indice_campanha * 0.01 + indice * 0.001:.6f}"),
                    "longitude": Decimal(f"{-38.53 + indice_campanha * 0.01 + indice * 0.001:.6f}"),
                },
            )
            InteracaoContato.todos_objetos.get_or_create(
                campanha=campanha,
                contato=contato,
                tipo="ligacao",
                data_hora=self.agora - timedelta(days=indice + 1),
                defaults={
                    "descricao": "Contato inicial de qualificacao e verificacao de interesse na campanha.",
                    "responsavel": usuarios[Usuario.NiveisAcesso.MOBILIZADOR],
                },
            )
            TarefaContato.todos_objetos.get_or_create(
                campanha=campanha,
                contato=contato,
                titulo=f"Retorno demo para {contato.nome_completo}",
                defaults={
                    "prazo": self.agora + timedelta(days=(indice % 5) + 1),
                    "concluida": indice % 4 == 0,
                    "responsavel": usuarios[Usuario.NiveisAcesso.COMUNICACAO],
                },
            )
            contatos.append(contato)
        return contatos

    def _criar_eventos(
        self,
        campanha: Campanha,
        usuarios: dict[str, Usuario],
        liderancas: list[Lideranca],
        indice_campanha: int,
    ) -> list[EventoAgenda]:
        municipio, bairros = self.MUNICIPIOS[indice_campanha % len(self.MUNICIPIOS)]
        tipos = list(EventoAgenda.Tipos.values)
        status = list(EventoAgenda.Status.values)
        eventos = []
        participantes = list(usuarios.values())[:4]

        for indice in range(self.opcoes.eventos):
            data_evento = self.hoje + timedelta(days=indice + 1)
            evento, _ = EventoAgenda.todos_objetos.get_or_create(
                campanha=campanha,
                titulo=f"Agenda demo {municipio} {indice + 1}",
                data=data_evento,
                defaults={
                    "descricao": "Evento demonstrativo da agenda compartilhada da campanha.",
                    "tipo": tipos[indice % len(tipos)],
                    "horario_inicial": time(9 + (indice % 5), 0),
                    "horario_final": time(10 + (indice % 5), 30),
                    "endereco": f"Praca central - {bairro_ou_padrao(bairros, indice)}",
                    "link_localizacao": "https://maps.example.local/demo",
                    "responsavel": usuarios[Usuario.NiveisAcesso.COORDENADOR_GERAL],
                    "status": status[indice % len(status)],
                    "prioridade": ["baixa", "media", "alta"][indice % 3],
                    "checklist": ["Confirmar equipe", "Validar som", "Registrar fotos"],
                    "observacoes": "Planejamento demonstrativo para apresentacao interna.",
                    "latitude": Decimal(f"{-3.73 + indice_campanha * 0.01 + indice * 0.001:.6f}"),
                    "longitude": Decimal(f"{-38.55 + indice_campanha * 0.01 + indice * 0.001:.6f}"),
                },
            )
            evento.participantes.set(participantes)
            evento.liderancas_convidadas.set(liderancas[: min(3, len(liderancas))])
            eventos.append(evento)
        return eventos

    def _criar_integrantes(
        self,
        campanha: Campanha,
        usuarios: dict[str, Usuario],
        indice_campanha: int,
    ) -> list[IntegranteEquipe]:
        municipio, _ = self.MUNICIPIOS[indice_campanha % len(self.MUNICIPIOS)]
        integrantes = []
        usuarios_base = list(usuarios.values())

        for indice in range(self.opcoes.integrantes):
            usuario_associado = usuarios_base[indice % len(usuarios_base)]
            email = f"integrante-{indice_campanha + 1}-{indice + 1}@demo.plataformacampanha.local"
            integrante, _ = IntegranteEquipe.todos_objetos.get_or_create(
                campanha=campanha,
                email=email,
                defaults={
                    "nome": f"{self._nome_pessoa(indice_campanha + indice + 50)} {self._sobrenome(indice + 5)}",
                    "telefone": self._telefone("85", indice_campanha, indice, base=83),
                    "funcao": self.FUNCOES_EQUIPE[indice % len(self.FUNCOES_EQUIPE)],
                    "departamento": self.DEPARTAMENTOS[indice % len(self.DEPARTAMENTOS)],
                    "cidade_regiao": municipio,
                    "data_entrada": self.hoje - timedelta(days=20 + indice),
                    "status": "ativo",
                    "disponibilidade": "Semana inteira",
                    "observacoes": "Integrante ficticio para demonstracao operacional.",
                    "usuario": usuario_associado,
                },
            )
            integrantes.append(integrante)

        if integrantes:
            lider = integrantes[0]
            for integrante in integrantes[1:]:
                if integrante.responsavel_direto_id != lider.id:
                    integrante.responsavel_direto = lider
                    integrante.save(update_fields=["responsavel_direto", "atualizado_em"])
        return integrantes

    def _criar_tarefas_equipe(self, campanha: Campanha, integrantes: list[IntegranteEquipe], indice_campanha: int):
        status = list(TarefaEquipe.Status.values)
        for indice in range(self.opcoes.tarefas):
            responsavel = integrantes[indice % len(integrantes)] if integrantes else None
            TarefaEquipe.todos_objetos.get_or_create(
                campanha=campanha,
                titulo=f"Tarefa demo {indice_campanha + 1}-{indice + 1}",
                defaults={
                    "descricao": "Atividade demonstrativa para o quadro Kanban da equipe.",
                    "responsavel": responsavel,
                    "prazo": self.agora + timedelta(days=(indice % 7) + 1),
                    "prioridade": ["baixa", "media", "alta"][indice % 3],
                    "status": status[indice % len(status)],
                    "checklist": ["Briefing", "Execucao", "Conferencia"],
                    "comentarios": "Gerado automaticamente para ambiente de treinamento.",
                },
            )
        self.resumo["tarefas"] += self.opcoes.tarefas

    def _criar_metas(
        self,
        campanha: Campanha,
        usuarios: dict[str, Usuario],
        integrantes: list[IntegranteEquipe],
        indice_campanha: int,
    ):
        tipos = list(MetaCampanha.Tipos.values)
        status = list(MetaCampanha.Status.values)
        for indice in range(self.opcoes.metas):
            valor_esperado = Decimal("50") + Decimal(indice * 10)
            valor_realizado = Decimal("20") + Decimal(indice * 7)
            MetaCampanha.todos_objetos.get_or_create(
                campanha=campanha,
                nome=f"Meta demo {indice_campanha + 1}-{indice + 1}",
                defaults={
                    "descricao": "Meta ficticia para medir produtividade e cadastros.",
                    "tipo": tipos[indice % len(tipos)],
                    "valor_esperado": valor_esperado,
                    "valor_realizado": valor_realizado,
                    "data_inicial": self.hoje - timedelta(days=15),
                    "data_final": self.hoje + timedelta(days=30 + indice),
                    "responsavel": usuarios[Usuario.NiveisAcesso.COORDENADOR_GERAL],
                    "equipe": integrantes[indice % len(integrantes)] if integrantes else None,
                    "regiao": f"Regional {indice_campanha + 1}",
                    "status": status[indice % len(status)],
                },
            )
        self.resumo["metas"] += self.opcoes.metas

    def _criar_financeiro(
        self,
        campanha: Campanha,
        usuarios: dict[str, Usuario],
        indice_campanha: int,
    ):
        categorias = [
            ("Arrecadacao demo", CategoriaFinanceira.Tipos.RECEITA),
            ("Publicidade demo", CategoriaFinanceira.Tipos.DESPESA),
            ("Mobilizacao demo", CategoriaFinanceira.Tipos.DESPESA),
            ("Doacao demo", CategoriaFinanceira.Tipos.DOACAO),
        ]
        categorias_obj = []
        for nome, tipo in categorias:
            categoria, _ = CategoriaFinanceira.todos_objetos.get_or_create(
                campanha=campanha,
                nome=nome,
                defaults={"tipo": tipo},
            )
            categorias_obj.append(categoria)

        centros = []
        for codigo, nome in [("COORD", "Coordenacao"), ("RUA", "Rua"), ("DIG", "Digital")]:
            centro, _ = CentroCusto.todos_objetos.get_or_create(
                campanha=campanha,
                codigo=f"{codigo}-{indice_campanha + 1}",
                defaults={"nome": f"{nome} demo"},
            )
            centros.append(centro)

        parceiros = []
        for indice in range(3):
            parceiro, _ = ParceiroFinanceiro.todos_objetos.get_or_create(
                campanha=campanha,
                nome=f"Parceiro demo {indice_campanha + 1}-{indice + 1}",
                defaults={
                    "documento": f"00.000.000/{indice_campanha:04d}-{indice:02d}",
                    "tipo": list(ParceiroFinanceiro.Tipos.values)[indice % len(ParceiroFinanceiro.Tipos.values)],
                    "telefone": self._telefone("85", indice_campanha, indice, base=79),
                    "email": f"financeiro-{indice_campanha + 1}-{indice + 1}@demo.plataformacampanha.local",
                },
            )
            parceiros.append(parceiro)

        tipos = list(LancamentoFinanceiro.Tipos.values)
        status = list(LancamentoFinanceiro.Status.values)
        for indice in range(self.opcoes.lancamentos):
            tipo = tipos[indice % len(tipos)]
            LancamentoFinanceiro.todos_objetos.get_or_create(
                campanha=campanha,
                numero_documento=f"DOC-DEMO-{indice_campanha + 1}-{indice + 1}",
                defaults={
                    "descricao": f"Lancamento demo {indice_campanha + 1}-{indice + 1}",
                    "tipo": tipo,
                    "categoria": categorias_obj[indice % len(categorias_obj)],
                    "valor_reais": Decimal("150.00") + Decimal(indice * 37),
                    "data_vencimento": self.hoje + timedelta(days=(indice % 10) - 3),
                    "data_pagamento": self.hoje - timedelta(days=1) if indice % 3 == 0 else None,
                    "parceiro": parceiros[indice % len(parceiros)],
                    "responsavel_lancamento": usuarios[Usuario.NiveisAcesso.FINANCEIRO],
                    "centro_custo": centros[indice % len(centros)],
                    "status": status[indice % len(status)],
                    "forma_pagamento": ["pix", "boleto", "transferencia"][indice % 3],
                    "observacoes": "Registro ficticio para demonstracao do modulo financeiro.",
                },
            )
        self.resumo["lancamentos"] += self.opcoes.lancamentos

    def _criar_comunicacao(
        self,
        campanha: Campanha,
        usuarios: dict[str, Usuario],
        contatos: list[ContatoCRM],
        indice_campanha: int,
    ):
        modelo, _ = ModeloMensagem.todos_objetos.get_or_create(
            campanha=campanha,
            nome=f"Modelo demo {indice_campanha + 1}",
            defaults={
                "assunto": "Mensagem demonstrativa da campanha",
                "conteudo": "Ola, esta e uma mensagem ficticia para apresentar o modulo de comunicacao.",
                "canal": CanalComunicacao.WHATSAPP,
            },
        )

        destinatarios_validos = [contato for contato in contatos if contato.consentimento_comunicacao][: max(1, min(5, len(contatos)))]
        if contatos:
            ListaBloqueio.todos_objetos.get_or_create(
                campanha=campanha,
                contato=contatos[0],
                canal=CanalComunicacao.WHATSAPP,
                defaults={
                    "motivo": "Exemplo de descadastro demonstrativo",
                    "solicitado_por": usuarios[Usuario.NiveisAcesso.COMUNICACAO],
                },
            )

        for indice in range(self.opcoes.comunicacoes):
            campanha_comunicacao, _ = CampanhaComunicacao.todos_objetos.get_or_create(
                campanha=campanha,
                nome=f"Comunicacao demo {indice_campanha + 1}-{indice + 1}",
                defaults={
                    "assunto": f"Atualizacao territorial {indice + 1}",
                    "conteudo": "Conteudo ficticio com orientacoes de mobilizacao e agenda.",
                    "canal": CanalComunicacao.WHATSAPP,
                    "modelo_mensagem": modelo,
                    "data_envio": self.agora + timedelta(days=indice + 1),
                    "responsavel": usuarios[Usuario.NiveisAcesso.COMUNICACAO],
                    "status": CampanhaComunicacao.Status.AGENDADA if indice == 0 else CampanhaComunicacao.Status.CONCLUIDA,
                    "permitir_cancelamento_inscricao": True,
                    "observacoes_internas": "Campanha ficticia para ambiente de homologacao.",
                },
            )
            campanha_comunicacao.destinatarios.set(destinatarios_validos)

            for indice_envio, contato in enumerate(destinatarios_validos):
                envio, _ = EnvioComunicacao.todos_objetos.get_or_create(
                    campanha=campanha,
                    campanha_comunicacao=campanha_comunicacao,
                    contato=contato,
                    defaults={
                        "canal": CanalComunicacao.WHATSAPP,
                        "status": [
                            EnvioComunicacao.Status.PROGRAMADO,
                            EnvioComunicacao.Status.ENTREGUE,
                            EnvioComunicacao.Status.RESPONDIDO,
                            EnvioComunicacao.Status.FALHA,
                        ][indice_envio % 4],
                        "mensagem_enviada": "Mensagem ficticia de campanha com consentimento previo.",
                        "erro_envio": "Falha simulada de operadora" if indice_envio % 4 == 3 else "",
                        "resposta_recebida": "Tenho interesse em participar." if indice_envio % 4 == 2 else "",
                        "data_programada": self.agora + timedelta(hours=indice_envio),
                        "responsavel_registro": usuarios[Usuario.NiveisAcesso.COMUNICACAO],
                    },
                )
                if envio.cancelou_inscricao != (indice_envio == len(destinatarios_validos) - 1 and indice == self.opcoes.comunicacoes - 1):
                    envio.cancelou_inscricao = indice_envio == len(destinatarios_validos) - 1 and indice == self.opcoes.comunicacoes - 1
                    envio.save(update_fields=["cancelou_inscricao", "atualizado_em"])
            campanha_comunicacao.atualizar_metricas()
            self.resumo["campanhas_comunicacao"] += 1

    def _criar_governanca(
        self,
        campanha: Campanha,
        usuarios: dict[str, Usuario],
        contatos: list[ContatoCRM],
        indice_campanha: int,
    ):
        politicas = [
            (
                f"Politica demo CRM {indice_campanha + 1}",
                PoliticaRetencaoDados.TiposRegistro.CONTATOS,
                "Consentimento e legitimo interesse eleitoral",
                365,
                180,
            ),
            (
                f"Politica demo financeiro {indice_campanha + 1}",
                PoliticaRetencaoDados.TiposRegistro.FINANCEIRO,
                "Obrigacao legal e prestacao de contas",
                1825,
                0,
            ),
        ]
        for nome, tipo_registro, base_legal, dias_retencao, dias_anonimizacao in politicas:
            PoliticaRetencaoDados.todos_objetos.get_or_create(
                campanha=campanha,
                nome=nome,
                defaults={
                    "tipo_registro": tipo_registro,
                    "base_legal": base_legal,
                    "dias_retencao": dias_retencao,
                    "dias_ate_anonimizacao": dias_anonimizacao,
                    "anonimizar_ao_expirar": dias_anonimizacao > 0,
                    "observacoes": "Politica ficticia utilizada para treinamento da equipe.",
                    "responsavel": usuarios[Usuario.NiveisAcesso.COORDENADOR_GERAL],
                },
            )

        contato_exemplo = contatos[1] if len(contatos) > 1 else contatos[0] if contatos else None
        if contato_exemplo:
            SolicitacaoTitularDados.todos_objetos.get_or_create(
                campanha=campanha,
                nome_solicitante=contato_exemplo.nome_completo,
                tipo_solicitacao=SolicitacaoTitularDados.TiposSolicitacao.ACESSO,
                defaults={
                    "email_solicitante": contato_exemplo.email,
                    "telefone_solicitante": contato_exemplo.telefone,
                    "canal_origem": "Portal interno demo",
                    "status": SolicitacaoTitularDados.Status.EM_ANALISE,
                    "descricao": "Solicitacao ficticia para demonstrar o atendimento aos direitos do titular.",
                    "contato_relacionado": contato_exemplo,
                    "responsavel_interno": usuarios[Usuario.NiveisAcesso.COORDENADOR_GERAL],
                    "prazo_resposta": self.hoje + timedelta(days=10),
                    "resposta_interna": "Aguardando consolidacao das informacoes solicitadas.",
                },
            )

        registro, criado_registro = RegistroAuditoria.todos_objetos.get_or_create(
            campanha=campanha,
            acao="seed_demo",
            modelo="Campanha",
            objeto_id=str(campanha.id),
            defaults={
                "resumo": "Carga de dados demonstrativos aplicada ao ambiente.",
                "dados_anteriores": {},
                "dados_novos": {"campanha": campanha.nome_campanha, "origem": "popular_dados_demo"},
                "usuario": usuarios[Usuario.NiveisAcesso.COORDENADOR_GERAL],
                "endereco_ip": "127.0.0.1",
            },
        )
        log, criado_log = LogSeguranca.todos_objetos.get_or_create(
            campanha=campanha,
            evento=f"seed_demo_{indice_campanha + 1}",
            defaults={
                "severidade": "info",
                "descricao": "Carga ficticia utilizada para treinamento e homologacao do sistema.",
                "usuario": usuarios[Usuario.NiveisAcesso.COORDENADOR_GERAL],
                "endereco_ip": "127.0.0.1",
            },
        )
        self.resumo["registros_auditoria"] += 1 if criado_registro else 0
        self.resumo["logs_seguranca"] += 1 if criado_log else 0

    def _nome_pessoa(self, indice: int) -> str:
        return self.NOMES[indice % len(self.NOMES)]

    def _sobrenome(self, indice: int) -> str:
        return self.SOBRENOMES[indice % len(self.SOBRENOMES)]

    def _telefone(self, ddd: str, indice_campanha: int, indice: int, base: int) -> str:
        return f"{ddd}9{base:02d}{indice_campanha + 1:02d}{indice + 1:04d}"


def bairro_ou_padrao(bairros: list[str], indice: int) -> str:
    return bairros[indice % len(bairros)] if bairros else "Centro"


def slug_ascii(valor: str) -> str:
    texto = unicodedata.normalize("NFKD", valor).encode("ascii", "ignore").decode("ascii")
    return "".join(caractere.lower() if caractere.isalnum() else "-" for caractere in texto).strip("-")
