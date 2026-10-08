import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# Configuração da Página
st.set_page_config(page_title="Gestão de Estoque | Íntima", page_icon="👙", layout="wide")

# --- CONEXÃO COM O GOOGLE SHEETS ---
# COLE O LINK DA SUA PLANILHA AQUI ABAIXO:
URL_PLANILHA = "https://docs.google.com/spreadsheets/d/1uQoccjhF7GZl4xQfzBdNmaY6xy2fWow1NwQ-cksuPlM/edit?usp=sharing"

conn = st.connection("gsheets", type=GSheetsConnection)

def carregar_dados():
    try:
        df_prod = conn.read(spreadsheet=URL_PLANILHA, worksheet="Produtos", ttl=0)
        df_mov = conn.read(spreadsheet=URL_PLANILHA, worksheet="Movimentacoes", ttl=0)
    except Exception as e:
        df_prod = pd.DataFrame(columns=['id', 'sku', 'nome', 'categoria', 'tamanho', 'cor', 'preco_custo', 'preco_venda', 'estoque_atual'])
        df_mov = pd.DataFrame(columns=['produto_id', 'tipo', 'quantidade', 'data_hora', 'cliente_nome', 'cliente_telefone', 'forma_pagamento', 'valor_total'])
    return df_prod, df_mov

df_prod, df_mov = carregar_dados()

# --- MENU LATERAL ---
st.sidebar.title("✨ Íntima Estoque")
st.sidebar.markdown("Bem-vindo ao controle gerencial.")
menu = ["📊 Dashboard", "📦 Entrada / Saída", "➕ Nova Peça", "📑 Relatório Mensal"]
escolha = st.sidebar.radio("Navegação Principal", menu)
st.sidebar.divider()
st.sidebar.caption("Desenvolvido por Kayo")

# --- 1. DASHBOARD ---
if escolha == "📊 Dashboard":
    st.title("📊 Visão Geral do Estoque")
    
    if not df_prod.empty and 'estoque_atual' in df_prod.columns:
        df_prod['estoque_atual'] = pd.to_numeric(df_prod['estoque_atual'], errors='coerce').fillna(0)
        
        # Alerta de Estoque Baixo
        baixo_estoque = df_prod[df_prod['estoque_atual'] <= 2]
        if not baixo_estoque.empty:
            st.warning("⚠️ **Atenção! As seguintes peças estão acabando (2 ou menos em estoque):**")
            for index, row in baixo_estoque.iterrows():
                st.write(f"- {row['nome']} (Tamanho {row['tamanho']}) | Restam: **{int(row['estoque_atual'])}** un.")
            st.divider()

        df_prod['preco_custo'] = pd.to_numeric(df_prod['preco_custo'], errors='coerce').fillna(0)
        df_prod['preco_venda'] = pd.to_numeric(df_prod['preco_venda'], errors='coerce').fillna(0)
        
        total_pecas = int(df_prod['estoque_atual'].sum())
        valor_custo = float((df_prod['preco_custo'] * df_prod['estoque_atual']).sum())
        valor_venda = float((df_prod['preco_venda'] * df_prod['estoque_atual']).sum())
    else:
        total_pecas, valor_custo, valor_venda = 0, 0.0, 0.0
        
    col1, col2, col3 = st.columns(3)
    col1.metric("Total de Peças Físicas", f"{total_pecas} un.")
    col2.metric("Valor Investido (Custo)", f"R$ {valor_custo:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    col3.metric("Faturamento Previsto (Venda)", f"R$ {valor_venda:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    
    st.divider()
    st.markdown("### Suas Peças em Estoque")
    st.dataframe(df_prod, use_container_width=True, hide_index=True)

# --- 2. MOVIMENTAÇÕES ---
elif escolha == "📦 Entrada / Saída":
    st.title("📦 Registrar Movimentação")
    
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
            
            cliente_nome = ""
            cliente_telefone = ""
            forma_pagamento = ""
            valor_total = 0.0
            
            if "Saída" in tipo:
                st.markdown("---")
                st.markdown("### 🛒 Dados da Venda")
                col3, col4 = st.columns(2)
                with col3:
                    cliente_nome = st.text_input("Nome da Cliente")
                    cliente_telefone = st.text_input("WhatsApp (com DDD)")
                with col4:
                    forma_pagamento = st.selectbox("Pagamento", ["Pix", "Dinheiro", "Cartão de Crédito", "Cartão de Débito", "Fiado / A Receber", "Uso Próprio"])
                    prod_id_temp = int(selecao.split(" - ")[0])
                    preco_sugerido = df_prod[df_prod['id'] == prod_id_temp]['preco_venda'].values[0]
                    valor_total = st.number_input("Valor Cobrado (R$)", min_value=0.0, value=float(preco_sugerido * qtd), format="%.2f")
            
            st.markdown("<br>", unsafe_allow_html=True) 
            
            if st.button("Confirmar Movimentação", type="primary", use_container_width=True):
                prod_id = int(selecao.split(" - ")[0])
                idx = df_prod[df_prod['id'] == prod_id].index[0]
                estoque_atual = int(df_prod.at[idx, 'estoque_atual'])
                
                if "Saída" in tipo and qtd > estoque_atual:
                    st.error(f"❌ Erro: Só tem {estoque_atual} no estoque!")
                else:
                    novo_estoque = estoque_atual + qtd if "Entrada" in tipo else estoque_atual - qtd
                    data_atual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    # Atualiza o dataframe de produtos
                    df_prod.at[idx, 'estoque_atual'] = novo_estoque
                    conn.update(spreadsheet=URL_PLANILHA, worksheet="Produtos", data=df_prod)
                    
                    # Registra a movimentação
                    nova_mov = pd.DataFrame([{
                        'produto_id': prod_id,
                        'tipo': "Entrada" if "Entrada" in tipo else "Saída",
                        'quantidade': qtd,
                        'data_hora': data_atual,
                        'cliente_nome': cliente_nome,
                        'cliente_telefone': cliente_telefone,
                        'forma_pagamento': forma_pagamento,
                        'valor_total': valor_total
                    }])
                    
                    df_mov_atualizado = pd.concat([df_mov, nova_mov], ignore_index=True)
                    conn.update(spreadsheet=URL_PLANILHA, worksheet="Movimentacoes", data=df_mov_atualizado)
                    
                    st.success(f"✅ Registrado com sucesso no Google Sheets! Novo saldo: {novo_estoque} unidades.")
                    st.rerun()

# --- 3. NOVA PEÇA ---
elif escolha == "➕ Nova Peça":
    st.title("➕ Cadastrar Nova Peça")
    with st.container(border=True):
        col1, col2 = st.columns(2)
        with col1:
            nome = st.text_input("Nome da Peça")
            categoria = st.selectbox("Categoria", ["Pijama", "Calcinha", "Sutiã", "Conjunto", "Baby Doll"])
            cor = st.text_input("Cor Predominante")
        with col2:
            tamanho = st.selectbox("Tamanho", ["Único", "PP", "P", "M", "G", "GG", "EXG"])
            custo = st.number_input("Preço de Custo (R$)", min_value=0.0, format="%.2f")
            venda = st.number_input("Preço de Venda (R$)", min_value=0.0, format="%.2f")
            
        estoque_inicial = st.number_input("Estoque Inicial", min_value=0, step=1)
        st.markdown("<br>", unsafe_allow_html=True)
        
        if st.button("💾 Salvar Produto", type="primary"):
            if nome == "" or cor == "":
                st.error("Preencha o nome e a cor!")
            else:
                novo_id = len(df_prod) + 1
                sku = f"{categoria[:3].upper()}-{tamanho}-{cor[:3].upper()}"
                
                novo_prod = pd.DataFrame([{
                    'id': novo_id,
                    'sku': sku,
                    'nome': nome,
                    'categoria': categoria,
                    'tamanho': tamanho,
                    'cor': cor,
                    'preco_custo': custo,
                    'preco_venda': venda,
                    'estoque_atual': estoque_inicial
                }])
                
                df_prod_atualizado = pd.concat([df_prod, novo_prod], ignore_index=True)
                conn.update(spreadsheet=URL_PLANILHA, worksheet="Produtos", data=df_prod_atualizado)
                
                if estoque_inicial > 0:
                    data_atual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    nova_mov = pd.DataFrame([{
                        'produto_id': novo_id,
                        'tipo': 'Entrada Inicial',
                        'quantidade': estoque_inicial,
                        'data_hora': data_atual,
                        'cliente_nome': '',
                        'cliente_telefone': '',
                        'forma_pagamento': '',
                        'valor_total': 0.0
                    }])
                    df_mov_atualizado = pd.concat([df_mov, nova_mov], ignore_index=True)
                    conn.update(spreadsheet=URL_PLANILHA, worksheet="Movimentacoes", data=df_mov_atualizado)
                
                st.success(f"✅ Produto cadastrado com sucesso no Google Sheets! SKU: **{sku}**")
                st.rerun()

# --- 4. RELATÓRIO MENSAL ---
elif escolha == "📑 Relatório Mensal":
    st.title("📑 Relatório de Vendas e Fechamento")
    
    if df_mov.empty or 'tipo' not in df_mov.columns:
        st.info("Nenhuma venda registrada ainda.")
    else:
        df_vendas = df_mov[df_mov['tipo'] == 'Saída'].copy()
        
        if df_vendas.empty:
            st.info("Nenhuma saída/venda registrada ainda.")
        else:
            df_vendas['data_hora'] = pd.to_datetime(df_vendas['data_hora'])
            df_vendas['Mes_Ano'] = df_vendas['data_hora'].dt.strftime('%m/%Y')
            
            meses_disponiveis = df_vendas['Mes_Ano'].unique()
            mes_selecionado = st.selectbox("Selecione o Mês para analisar:", meses_disponiveis)
            
            df_mes = df_vendas[df_vendas['Mes_Ano'] == mes_selecionado].copy()
            df_mes['valor_total'] = pd.to_numeric(df_mes['valor_total'], errors='coerce').fillna(0)
            
            faturamento_total = df_mes['valor_total'].sum()
            fiado_df = df_mes[df_mes['forma_pagamento'] == 'Fiado / A Receber']
            total_fiado = fiado_df['valor_total'].sum()
            caixa_real = faturamento_total - total_fiado
            
            col_a, col_b, col_c = st.columns(3)
            col_a.metric("Faturamento do Mês", f"R$ {faturamento_total:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
            col_b.metric("Caixa Real (Recebido)", f"R$ {caixa_real:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
            col_c.metric("🔴 A Receber (Fiado)", f"R$ {total_fiado:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
            
            st.markdown("---")
            st.markdown("### Detalhamento das Vendas")
            
            df_export = df_mes.drop(columns=['Mes_Ano']).copy()
            df_export['data_hora'] = df_export['data_hora'].dt.strftime('%d/%m/%Y %H:%M')
            
            st.dataframe(df_export, use_container_width=True, hide_index=True)
            
            csv_relatorio = df_export.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Baixar Relatório em Excel/CSV",
                data=csv_relatorio,
                file_name=f"relatorio_vendas_{mes_selecionado.replace('/','_')}.csv",
                mime="text/csv",
                use_container_width=True
            )
