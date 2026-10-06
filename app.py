import sqlite3
import streamlit as st
import pandas as pd
from datetime import datetime

# Configuração da Página (DEVE SER A PRIMEIRA LINHA DO STREAMLIT)
st.set_page_config(page_title="Gestão de Estoque | Íntima", page_icon="👙", layout="wide")

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

# --- MENU LATERAL ---
st.sidebar.title("✨ Íntima Estoque")
st.sidebar.markdown("Bem-vindo ao seu controle gerencial.")
menu = ["📊 Dashboard", "📦 Entrada / Saída", "➕ Nova Peça"]
escolha = st.sidebar.radio("Navegação Principal", menu)
st.sidebar.divider()
st.sidebar.caption("Desenvolvido por Kayo")

# --- 1. DASHBOARD (Visão Geral) ---
if escolha == "📊 Dashboard":
    st.title("📊 Visão Geral do Estoque")
    
    df_prod = pd.read_sql_query("SELECT * FROM produtos", conn)
    
    # Cards de Métricas
    col1, col2, col3 = st.columns(3)
    if not df_prod.empty:
        total_pecas = int(df_prod['estoque_atual'].sum())
        valor_custo = (df_prod['preco_custo'] * df_prod['estoque_atual']).sum()
        valor_venda = (df_prod['preco_venda'] * df_prod['estoque_atual']).sum()
    else:
        total_pecas, valor_custo, valor_venda = 0, 0.0, 0.0
        
    col1.metric("Total de Peças Físicas", f"{total_pecas} un.")
    col2.metric("Valor Investido (Custo)", f"R$ {valor_custo:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    col3.metric("Faturamento Previsto (Venda)", f"R$ {valor_venda:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    
    st.divider()
    
    # Organização em Abas
    tab1, tab2 = st.tabs(["📋 Inventário Completo", "🕰️ Histórico de Movimentações"])
    
    with tab1:
        st.markdown("### Suas Peças em Estoque")
        df_view = pd.read_sql_query("SELECT sku as SKU, nome as Nome, categoria as Categoria, tamanho as Tamanho, cor as Cor, estoque_atual as Saldo, preco_custo as Custo, preco_venda as Venda FROM produtos", conn)
        st.dataframe(df_view, use_container_width=True, hide_index=True)
        
    with tab2:
        st.markdown("### Últimas Entradas e Saídas")
        df_mov = pd.read_sql_query('''
            SELECT m.data_hora as Data, p.sku as SKU, p.nome as Produto, m.tipo as Operação, m.quantidade as Qtd 
            FROM movimentacoes m 
            JOIN produtos p ON m.produto_id = p.id 
            ORDER BY m.id DESC LIMIT 50
        ''', conn)
        # Destacar saídas em vermelho e entradas em verde seria complexo sem pandas styling, 
        # mas o dataframe padrão já é muito limpo.
        st.dataframe(df_mov, use_container_width=True, hide_index=True)

# --- 2. MOVIMENTAÇÕES ---
elif escolha == "📦 Entrada / Saída":
    st.title("📦 Registrar Movimentação")
    st.markdown("Registre vendas ou chegadas de novos pedidos do fornecedor.")
    
    df_prod = pd.read_sql_query("SELECT id, sku, nome, estoque_atual FROM produtos", conn)
    
    if df_prod.empty:
        st.warning("⚠️ Nenhuma peça cadastrada. Vá para 'Nova Peça' primeiro.")
    else:
        with st.container(border=True):
            opcoes = df_prod['id'].astype(str) + " - " + df_prod['sku'] + " (" + df_prod['nome'] + ") | Saldo: " + df_prod['estoque_atual'].astype(str)
            selecao = st.selectbox("Selecione o Produto", opcoes)
            
            col1, col2 = st.columns(2)
            with col1:
                tipo = st.radio("Qual é a operação?", ["Entrada (Chegou estoque/Devolução)", "Saída (Venda/Descarte)"])
            with col2:
                qtd = st.number_input("Quantidade de Peças", min_value=1, step=1)
                
            st.markdown("<br>", unsafe_allow_html=True) # Espaçamento
            
            # Botão em destaque
            if st.button("Confirmar Movimentação", type="primary", use_container_width=True):
                prod_id = int(selecao.split(" - ")[0])
                estoque_atual = df_prod[df_prod['id'] == prod_id]['estoque_atual'].values[0]
                
                if "Saída" in tipo and qtd > estoque_atual:
                    st.error(f"❌ Erro: Você tentou dar saída em {qtd} peças, mas só tem {estoque_atual} no estoque!")
                else:
                    novo_estoque = estoque_atual + qtd if "Entrada" in tipo else estoque_atual - qtd
                    data_atual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    c.execute("UPDATE produtos SET estoque_atual=? WHERE id=?", (novo_estoque, prod_id))
                    c.execute("INSERT INTO movimentacoes (produto_id, tipo, quantidade, data_hora) VALUES (?, ?, ?, ?)",
                              (prod_id, "Entrada" if "Entrada" in tipo else "Saída", qtd, data_atual))
                    conn.commit()
                    st.success(f"✅ Sucesso! O novo saldo desta peça é de {novo_estoque} unidades.")

# --- 3. CADASTRAR PRODUTO ---
elif escolha == "➕ Nova Peça":
    st.title("➕ Cadastrar Nova Peça")
    st.markdown("Preencha as informações para adicionar um novo modelo ao catálogo.")
    
    with st.container(border=True):
        col1, col2 = st.columns(2)
        with col1:
            nome = st.text_input("Nome da Peça (ex: Pijama Seda Oncinha)")
            categoria = st.selectbox("Categoria", ["Pijama", "Calcinha", "Sutiã", "Conjunto", "Baby Doll"])
            cor = st.text_input("Cor Predominante")
        with col2:
            tamanho = st.selectbox("Tamanho", ["Único", "PP", "P", "M", "G", "GG", "EXG"])
            custo = st.number_input("Preço de Custo (R$)", min_value=0.0, format="%.2f")
            venda = st.number_input("Preço de Venda (R$)", min_value=0.0, format="%.2f")
            
        estoque_inicial = st.number_input("Quantas peças você tem agora? (Estoque Inicial)", min_value=0, step=1)

        st.markdown("<br>", unsafe_allow_html=True)
        
        if st.button("💾 Salvar Produto no Catálogo", type="primary"):
            if nome == "" or cor == "":
                st.error("Preencha o nome e a cor!")
            else:
                sku = f"{categoria[:3].upper()}-{tamanho}-{cor[:3].upper()}"
                c.execute("INSERT INTO produtos (sku, nome, categoria, tamanho, cor, preco_custo, preco_venda, estoque_atual) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                          (sku, nome, categoria, tamanho, cor, custo, venda, estoque_inicial))
                produto_id = c.lastrowid
                
                if estoque_inicial > 0:
                    data_atual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    c.execute("INSERT INTO movimentacoes (produto_id, tipo, quantidade, data_hora) VALUES (?, ?, ?, ?)",
                              (produto_id, 'Entrada Inicial', estoque_inicial, data_atual))
                    
                conn.commit()
                st.success(f"✅ Produto cadastrado com sucesso! Código Gerado (SKU): **{sku}**")