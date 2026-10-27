import sqlite3
import random
from datetime import datetime, timedelta

DB_FILE = "pcp_lavra.db"

# Listas de apoio baseadas na sua equipa
horarios = ["07:15", "08:00", "09:00", "10:00", "11:00", "13:00", "14:00", "15:00", "16:00"]
operadores_carga = ["Kadu", "Dionis", "Jaeiel", "Fernando"]
operadores_perf = ["Marcelino", "Adelson"]
causas_carga = ["", "", "", "", "", "Manutenção", "Baixando Pulmão", "Falta de Material"]
causas_perf = ["", "", "", "", "", "Manutenção", "Mudança de Praça", "Espera de Desmonte"]

# Horímetros iniciais (fictícios) de 6 meses atrás
hm_ut33, hm_ut34 = 15000.0, 12500.0
hm_motor_up09, hm_martelo_up09 = 8000.0, 4000.0

def gerar_dados():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Criar tabelas caso não existam
    cursor.execute("CREATE TABLE IF NOT EXISTS horaria_carga (data_id TEXT, hora TEXT, ut33 INTEGER, ut34 INTEGER, meta INTEGER, causa TEXT, PRIMARY KEY (data_id, hora))")
    cursor.execute("CREATE TABLE IF NOT EXISTS horaria_perf (data_id TEXT, hora TEXT, realizado REAL, meta REAL, causa TEXT, PRIMARY KEY (data_id, hora))")
    cursor.execute("CREATE TABLE IF NOT EXISTS parte_diaria (id INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT, operador TEXT, equipamento TEXT, hora_ini TEXT, hora_fim TEXT, hori_motor_ini REAL, hori_motor_fim REAL, hori_martelo_ini REAL, hori_martelo_fim REAL, obs_paradas TEXT)")

    data_inicio = datetime.today() - timedelta(days=180)

    print("A gerar 6 meses de dados para a Diretoria (Aguarde...)")
    
    for i in range(181):
        data_atual = data_inicio + timedelta(days=i)
        
        # Pular Domingos (na mineração geralmente é folga/manutenção)
        if data_atual.weekday() == 6:
            continue
            
        data_str = data_atual.strftime('%Y-%m-%d')

        # 1. GERAR HORA A HORA
        for hora in horarios:
            # Caminhões (Viagens)
            v33 = random.randint(8, 14) if random.random() > 0.15 else 0
            v34 = random.randint(8, 14) if random.random() > 0.15 else 0
            causa_c = random.choice(causas_carga) if (v33 == 0 or v34 == 0) else ""
            cursor.execute("INSERT OR REPLACE INTO horaria_carga (data_id, hora, ut33, ut34, meta, causa) VALUES (?, ?, ?, ?, ?, ?)", (data_str, hora, v33, v34, 13, causa_c))

            # Perfuratriz (Metros)
            metros = round(random.uniform(10.0, 17.0), 1) if random.random() > 0.15 else 0.0
            causa_p = random.choice(causas_perf) if metros == 0 else ""
            cursor.execute("INSERT OR REPLACE INTO horaria_perf (data_id, hora, realizado, meta, causa) VALUES (?, ?, ?, ?, ?)", (data_str, hora, metros, 15, causa_p))

        # 2. GERAR FECHAMENTO DE TURNO (Horímetros)
        global hm_ut33, hm_ut34, hm_motor_up09, hm_martelo_up09
        
        # UT-33
        hm_fim_33 = hm_ut33 + random.uniform(7.5, 9.0)
        cursor.execute("INSERT INTO parte_diaria (data, operador, equipamento, hora_ini, hora_fim, hori_motor_ini, hori_motor_fim, hori_martelo_ini, hori_martelo_fim, obs_paradas) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (data_str, random.choice(operadores_carga), "Caminhão Mercedes - UT-33", "07:00", "17:00", hm_ut33, hm_fim_33, 0, 0, ""))
        hm_ut33 = hm_fim_33

        # UT-34
        hm_fim_34 = hm_ut34 + random.uniform(7.5, 9.0)
        cursor.execute("INSERT INTO parte_diaria (data, operador, equipamento, hora_ini, hora_fim, hori_motor_ini, hori_motor_fim, hori_martelo_ini, hori_martelo_fim, obs_paradas) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (data_str, random.choice(operadores_carga), "Caminhão Mercedes - UT-34", "07:00", "17:00", hm_ut34, hm_fim_34, 0, 0, ""))
        hm_ut34 = hm_fim_34

        # UP-09
        hm_motor_fim = hm_motor_up09 + random.uniform(7.0, 9.0)
        hm_martelo_fim = hm_martelo_up09 + random.uniform(4.0, 6.0)
        cursor.execute("INSERT INTO parte_diaria (data, operador, equipamento, hora_ini, hora_fim, hori_motor_ini, hori_motor_fim, hori_martelo_ini, hori_martelo_fim, obs_paradas) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (data_str, random.choice(operadores_perf), "Perfuratriz Wolf - UP-09", "07:00", "17:00", hm_motor_up09, hm_motor_fim, hm_martelo_up09, hm_martelo_fim, ""))
        hm_motor_up09 = hm_motor_fim
        hm_martelo_up09 = hm_martelo_fim

    conn.commit()
    conn.close()
    print("✅ Sucesso! 6 meses de produção inseridos na base de dados.")

gerar_dados()