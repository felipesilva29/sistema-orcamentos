import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# Conexão com banco de dados SQLite (para Render, considere volume ou banco externo para persistência)
conn = sqlite3.connect('orcamentos_eventos.db', check_same_thread=False)
c = conn.cursor()

# Cria tabelas se não existirem
c.execute('''
CREATE TABLE IF NOT EXISTS eventos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT UNIQUE
)
''')

c.execute('''
CREATE TABLE IF NOT EXISTS orcamentos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT,
    responsavel TEXT,
    data_criacao DATE DEFAULT (date('now')),
    descricao TEXT,
    evento_vinculado TEXT,
    status TEXT DEFAULT 'Em Elaboração'
)
''')

c.execute('''
CREATE TABLE IF NOT EXISTS receitas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    orcamento_id INTEGER,
    fonte TEXT,
    valor_previsto REAL,
    FOREIGN KEY (orcamento_id) REFERENCES orcamentos(id)
)
''')

c.execute('''
CREATE TABLE IF NOT EXISTS despesas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    orcamento_id INTEGER,
    descricao TEXT,
    categoria TEXT,
    valor_previsto REAL,
    status TEXT DEFAULT 'Pendente',
    data_autorizada DATE,
    forma_pagamento TEXT,
    observacoes TEXT,
    FOREIGN KEY (orcamento_id) REFERENCES orcamentos(id)
)
''')
conn.commit()

# Funções auxiliares
def load_data(tabela, filtro=None):
    query = f"SELECT * FROM {tabela}"
    if filtro:
        query += f" WHERE {filtro}"
    df = pd.read_sql_query(query, conn)
    return df

def add_evento(nome):
    try:
        c.execute('INSERT INTO eventos (nome) VALUES (?)', (nome,))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False

def add_orcamento(nome, responsavel, descricao, evento):
    c.execute('''
    INSERT INTO orcamentos (nome, responsavel, descricao, evento_vinculado)
    VALUES (?, ?, ?, ?)
    ''', (nome, responsavel, descricao, evento))
    conn.commit()

def add_receita(orcamento_id, fonte, valor):
    c.execute('INSERT INTO receitas (orcamento_id, fonte, valor_previsto) VALUES (?, ?, ?)', (orcamento_id, fonte, valor))
    conn.commit()

def add_despesa(orcamento_id, descricao, categoria, valor):
    c.execute('INSERT INTO despesas (orcamento_id, descricao, categoria, valor_previsto) VALUES (?, ?, ?, ?)', (orcamento_id, descricao, categoria, valor))
    conn.commit()

def update_item(tabela, id, campo, valor):
    c.execute(f"UPDATE {tabela} SET {campo} = ? WHERE id = ?", (valor, id))
    conn.commit()

def delete_item(tabela, id):
    c.execute(f"DELETE FROM {tabela} WHERE id = ?", (id,))
    conn.commit()

# Interface principal
st.title("Sistema de Análise e Acompanhamento de Orçamentos - Criativa Mais Cultura")
st.markdown("**Fluxo:** Crie orçamentos, adicione receitas/despesas, aprove despesas individualmente. Status de despesas: Pendente → Aprovado → Lançado. Cálculos automáticos de totais e saldo.")

# Seção de Cadastro de Eventos
st.header("Cadastro de Eventos")
novo_evento = st.text_input("Nome do Novo Evento")
if st.button("Adicionar Evento"):
    if add_evento(novo_evento):
        st.success(f"Evento '{novo_evento}' adicionado!")
    else:
        st.warning(f"Evento '{novo_evento}' já existe.")

eventos_df = load_data('eventos')
st.subheader("Eventos Cadastrados")
st.dataframe(eventos_df[['nome']])

# Seção de Criação de Orçamento
st.header("Criar Novo Orçamento")
eventos_list = ["Sem evento vinculado"] + eventos_df['nome'].tolist()

with st.form(key='novo_orcamento'):
    nome_orc = st.text_input("Nome do Orçamento")
    responsavel = st.text_input("Responsável")
    descricao_orc = st.text_area("Descrição Geral")
    evento = st.selectbox("Evento Vinculado", eventos_list)
    submit_orc = st.form_submit_button("Criar Orçamento")

if submit_orc:
    add_orcamento(nome_orc, responsavel, descricao_orc, evento)
    st.success("Orçamento criado! Data de criação: " + datetime.now().strftime("%Y-%m-%d"))

# Lista de Orçamentos
orcamentos_df = load_data('orcamentos')

# Filtros de Busca
st.header("Buscar Orçamentos")
col1, col2, col3 = st.columns(3)
filtro_evento = col1.text_input("Filtrar por Evento")
filtro_data_criacao = col2.date_input("Filtrar por Data de Criação")
filtro_status = col3.selectbox("Filtrar por Status", ["Todos"] + orcamentos_df['status'].unique().tolist())

if filtro_evento:
    orcamentos_df = orcamentos_df[orcamentos_df['evento_vinculado'].str.contains(filtro_evento, case=False)]
if filtro_data_criacao:
    orcamentos_df = orcamentos_df[orcamentos_df['data_criacao'] == str(filtro_data_criacao)]
if filtro_status != "Todos":
    orcamentos_df = orcamentos_df[orcamentos_df['status'] == filtro_status]

st.dataframe(orcamentos_df)

# Seção de Detalhamento e Ações
st.header("Detalhamento e Ações em Orçamentos")
orcamento_id = st.number_input("ID do Orçamento para Detalhar/Ações", min_value=1, step=1)

if orcamento_id:
    orcamento = orcamentos_df[orcamentos_df['id'] == orcamento_id]
    if not orcamento.empty:
        st.subheader(f"Detalhes do Orçamento ID {orcamento_id}")
        st.write(f"Nome: {orcamento['nome'].values[0]} | Responsável: {orcamento['responsavel'].values[0]} | Evento: {orcamento['evento_vinculado'].values[0]} | Status: {orcamento['status'].values[0]} | Data Criação: {orcamento['data_criacao'].values[0]}")
        st.write(f"Descrição: {orcamento['descricao'].values[0]}")

        # Atualizar status do orçamento
        novo_status = st.selectbox("Atualizar Status do Orçamento", ["Em Elaboração", "Finalizado", "Cancelado"], index=0)
        if st.button("Salvar Status"):
            update_item('orcamentos', orcamento_id, 'status', novo_status)
            st.success("Status atualizado!")

        # Receitas
        st.subheader("Previsões de Receitas")
        receitas_df = load_data('receitas', f"orcamento_id = {orcamento_id}")
        st.dataframe(receitas_df[['id', 'fonte', 'valor_previsto']].style.format({"valor_previsto": "R$ {:.2f}"}))
        
        with st.form(key='nova_receita'):
            fonte = st.text_input("Fonte de Receita")
            valor_rec = st.number_input("Valor Previsto (R$)", min_value=0.0)
            submit_rec = st.form_submit_button("Adicionar Receita")
        if submit_rec:
            add_receita(orcamento_id, fonte, valor_rec)
            st.success("Receita adicionada!")

        # Despesas com fluxo de aprovação
        st.subheader("Previsões de Despesas")
        despesas_df = load_data('despesas', f"orcamento_id = {orcamento_id}")
        st.dataframe(despesas_df[['id', 'descricao', 'categoria', 'valor_previsto', 'status', 'data_autorizada', 'forma_pagamento', 'observacoes']].style.format({"valor_previsto": "R$ {:.2f}"}))

        with st.form(key='nova_despesa'):
            desc_des = st.text_input("Descrição da Despesa")
            categoria = st.selectbox("Categoria", ["Equipe", "Materiais", "Viagens", "Outros"])
            valor_des = st.number_input("Valor Previsto (R$)", min_value=0.0)
            submit_des = st.form_submit_button("Adicionar Despesa")
        if submit_des:
            add_despesa(orcamento_id, desc_des, categoria, valor_des)
            st.success("Despesa adicionada como Pendente!")

        # Ações em Despesas
        st.subheader("Ações em Despesas")
        despesa_id = st.number_input("ID da Despesa para Ação", min_value=1, step=1)
        if despesa_id:
            despesa = despesas_df[despesas_df['id'] == despesa_id]
            if not despesa.empty:
                status_des = despesa['status'].values[0]
                
                if status_des == 'Pendente':
                    acao = st.selectbox("Ação", ["Editar", "Excluir", "Cancelar", "Aprovar"])
                    
                    if acao == "Editar":
                        with st.form(key='edit_despesa'):
                            nova_desc = st.text_input("Nova Descrição", value=despesa['descricao'].values[0])
                            nova_cat = st.selectbox("Nova Categoria", ["Equipe", "Materiais", "Viagens", "Outros"], index=["Equipe", "Materiais", "Viagens", "Outros"].index(despesa['categoria'].values[0]))
                            novo_valor = st.number_input("Novo Valor", value=despesa['valor_previsto'].values[0])
                            submit_edit = st.form_submit_button("Salvar Edição")
                        if submit_edit:
                            update_item('despesas', despesa_id, 'descricao', nova_desc)
                            update_item('despesas', despesa_id, 'categoria', nova_cat)
                            update_item('despesas', despesa_id, 'valor_previsto', novo_valor)
                            st.success("Despesa editada!")
                    
                    elif acao == "Excluir":
                        if st.button("Confirmar Exclusão"):
                            delete_item('despesas', despesa_id)
                            st.success("Despesa excluída!")
                    
                    elif acao == "Cancelar":
                        if st.button("Confirmar Cancelamento"):
                            update_item('despesas', despesa_id, 'status', 'Cancelado')
                            st.success("Despesa cancelada!")
                    
                    elif acao == "Aprovar":
                        senha = st.text_input("Senha para Aprovação", type="password")
                        if senha == "criativa123":
                            with st.form(key='aprovar_despesa'):
                                data_aut = st.date_input("Data Autorizada")
                                forma_pag = st.selectbox("Forma de Pagamento", ["À vista", "Parcelado", "Faturado", "PIX", "Outros"])
                                submit_aprov = st.form_submit_button("Aprovar")
                            if submit_aprov:
                                update_item('despesas', despesa_id, 'data_autorizada', str(data_aut))
                                update_item('despesas', despesa_id, 'forma_pagamento', forma_pag)
                                update_item('despesas', despesa_id, 'status', 'Aprovado')
                                st.success("Despesa aprovada!")
                        else:
                            st.error("Senha incorreta.")
                
                elif status_des == 'Aprovado':
                    acao = st.selectbox("Ação", ["Adicionar Observações", "Marcar como Lançado"])
                    
                    if acao == "Adicionar Observações":
                        novas_obs = st.text_area("Observações", value=despesa['observacoes'].values[0] or "")
                        if st.button("Salvar Observações"):
                            update_item('despesas', despesa_id, 'observacoes', novas_obs)
                            st.success("Observações atualizadas!")
                    
                    elif acao == "Marcar como Lançado":
                        if st.button("Confirmar"):
                            update_item('despesas', despesa_id, 'status', 'Lançado')
                            st.success("Despesa lançada!")
                
                else:
                    st.info(f"Status: {status_des}. Nenhuma ação disponível.")

        # Análise e Cálculos
        st.subheader("Análise do Orçamento")
        total_receitas = receitas_df['valor_previsto'].sum() if not receitas_df.empty else 0
        total_despesas = despesas_df['valor_previsto'].sum() if not despesas_df.empty else 0
        saldo = total_receitas - total_despesas
        margem = (saldo / total_receitas * 100) if total_receitas > 0 else 0

        st.write(f"Total Receitas: R$ {total_receitas:.2f}")
        st.write(f"Total Despesas: R$ {total_despesas:.2f}")
        st.write(f"Saldo: R$ {saldo:.2f}")
        st.write(f"Margem de Lucro: {margem:.2f}%")

        # Gráfico simples
        if not receitas_df.empty or not despesas_df.empty:
            chart_data = pd.DataFrame({"Tipo": ["Receitas", "Despesas"], "Valor": [total_receitas, total_despesas]})
            st.bar_chart(chart_data.set_index("Tipo"))

    else:
        st.error("Orçamento não encontrado.")
