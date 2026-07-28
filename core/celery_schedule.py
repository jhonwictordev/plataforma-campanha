ROTINAS_CELERY = [
    {
        "nome": "Plataforma - Comunicacoes agendadas",
        "task": "core.tasks.sinalizar_campanhas_agendadas_task",
        "tipo": "interval",
        "every": 15,
        "period": "minutes",
    },
    {
        "nome": "Plataforma - Lembretes de agenda",
        "task": "core.tasks.gerar_lembretes_agenda_task",
        "tipo": "interval",
        "every": 30,
        "period": "minutes",
    },
    {
        "nome": "Plataforma - Alertas de tarefas",
        "task": "core.tasks.gerar_alertas_tarefas_task",
        "tipo": "interval",
        "every": 60,
        "period": "minutes",
    },
    {
        "nome": "Plataforma - Alertas financeiros",
        "task": "core.tasks.gerar_alertas_financeiros_task",
        "tipo": "crontab",
        "minute": "0",
        "hour": "8",
    },
    {
        "nome": "Plataforma - Alertas LGPD",
        "task": "core.tasks.gerar_alertas_lgpd_task",
        "tipo": "crontab",
        "minute": "0",
        "hour": "9",
    },
    {
        "nome": "Plataforma - Alertas de retencao",
        "task": "core.tasks.gerar_alertas_retencao_task",
        "tipo": "crontab",
        "minute": "15",
        "hour": "9",
    },
]
