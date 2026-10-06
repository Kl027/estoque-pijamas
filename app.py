import sqlite3
import streamlit as st
import pandas as pd
from datetime import datetime

# Conexão com o banco de dados
conn = sqlite3.connect("estoque_intimas.db")
c = conn.cursor()

# Criação das tabelas
c.execute('''CREATE TABLE IF NOT EXISTS produtos
             (id INTEGER PRIMARY KEY, sku TEXT, nome TEXT, categoria TEXT, 
             tamanho TEXT, cor TEXT, preco_custo REAL, preco_venda REAL, estoque_atual INTEGER)''')

c.execute('''CREATE TABLE IF NOT EXISTS movimentacoes
             (id INTEGER PRIMARY KEY AUTOINCREMENT, produto_id INTEGER, tipo TEXT, 
             quantidade INTEGER, data_hora TEXT)''')

st.set_page_config(page_title="Estoque - Pijamas & Lingeries", layout="wide")
st.title("Controle de Estoque - Pijamas & Lingeries")

menu = ["Cadastrar Produto", "Registrar Movimentação", "Visão Geral"]
escolha = st.sidebar.selectbox("Navegação", menu)

if escolha == "Cadastrar Produto":
    st.subheader("Nova Peça")
    nome = st.text_input("Nome da Peça (ex: Conjunto Renda)")
    categoria = st.selectbox("Categoria", ["Pijama", "Calcinha", "Sutiã", "Conjunto"])
    tamanho = st.selectbox("Tamanho", ["P", "M", "G", "GG"])
    cor = st.text_input("Cor")
    custo = st.number_input("Preço de Custo (R$)", min_value=0.0)
    venda = st.number_input("Preço de Venda (R$)", min_value=0.0)
    estoque_inicial = st.number_input("Estoque Inicial", min_value=0, step=1)

    if st.button("Salvar Produto"):
        sku = f"{categoria[:3].upper()}-{tamanho}-{cor[:3].upper()}"
        c.execute("INSERT INTO produtos (sku, nome, categoria, tamanho, cor, preco_custo, preco_venda, estoque_atual) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                  (sku, nome, categoria, tamanho, cor, custo, venda, estoque_inicial))
        produto_id = c.lastrowid
        
        # Registra a entrada inicial no histórico
        if estoque_inicial > 0:
            data_atual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            c.execute("INSERT INTO movimentacoes (produto_id, tipo, quantidade, data_hora) VALUES (?, ?, ?, ?)",
                      (produto_id, 'Entrada Inicial', estoque_inicial, data_atual))
            
        conn.commit()
        st.success(f"Produto {nome} cadastrado! SKU: {sku}")

elif escolha == "Registrar Movimentação":
    st.subheader("Entrada e Saída Diária")
    df_prod = pd.read_sql_query("SELECT id, sku, nome, estoque_atual FROM produtos", conn)
    
    if df_prod.empty:
        st.warning("Cadastre um produto primeiro.")
    else:
        opcoes = df_prod['id'].astype(str) + " - " + df_prod['sku'] + " (" + df_prod['nome'] + ")"
        selecao = st.selectbox("Selecione a Peça", opcoes)
        
        tipo = st.radio("Tipo de Movimentação", ["Entrada (Compra/Devolução)", "Saída (Venda/Descarte)"])
        qtd = st.number_input("Quantidade", min_value=1, step=1)
        
        if st.button("Confirmar"):
            prod_id = int(selecao.split(" - ")[0])
            estoque_atual = df_prod[df_prod['id'] == prod_id]['estoque_atual'].values[0]
            
            if "Saída" in tipo and qtd > estoque_atual:
                st.error("Erro: Quantidade de saída maior que o estoque disponível!")
            else:
                novo_estoque = estoque_atual + qtd if "Entrada" in tipo else estoque_atual - qtd
                data_atual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                c.execute("UPDATE produtos SET estoque_atual=? WHERE id=?", (novo_estoque, prod_id))
                c.execute("INSERT INTO movimentacoes (produto_id, tipo, quantidade, data_hora) VALUES (?, ?, ?, ?)",
                          (prod_id, tipo, qtd, data_atual))
                conn.commit()
                st.success(f"Registrado com sucesso! Novo saldo: {novo_estoque} peças.")

elif escolha == "Visão Geral":
    st.subheader("Inventário Atual")
    df = pd.read_sql_query("SELECT sku as SKU, nome as Nome, tamanho as Tamanho, estoque_atual as Estoque, preco_custo as Custo, preco_venda as Venda FROM produtos", conn)
    st.dataframe(df, use_container_width=True)
    
    st.subheader("Histórico de Movimentações (Extrato)")
    df_mov = pd.read_sql_query('''
        SELECT m.data_hora as Data, p.sku as SKU, m.tipo as Operação, m.quantidade as Qtd 
        FROM movimentacoes m 
        JOIN produtos p ON m.produto_id = p.id 
        ORDER BY m.id DESC LIMIT 50
    ''', conn)
    st.dataframe(df_mov, use_container_width=True)
