import streamlit as st
import requests
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
import matplotlib.pyplot as plt


# Função para calcular o custo de compra, receita das vendas, lucro e retorno percentual
def calcular_retorno_completo (preco_kg, peso_inicial, preco_final, tempo_meses, fee_criador):
    print(f"Taxa fee {fee_criador}")
    # Armazenar os resultados
    resultados_melhor_cenario = []
    resultados_pior_cenario = []

    # Estimativa de peso trimestral
    for trimestre in range(0, tempo_meses + 1, 3):
        peso_melhor_cenario = calcular_peso_trimestral(peso_inicial, trimestre, otimista=True)
        peso_pior_cenario = calcular_peso_trimestral(peso_inicial, trimestre, otimista=False)
    
        valor_compra = preco_kg * peso_inicial
        print(f"Taxa cliente {porcentagem_cliente(fee_criador)}")
        # Calculando o lucro com a regra de % sobre a diferença enter o peso final e o peso inicial
        # Você recebe uma % da diferença entre o peso da venda e o peso inicial que o criador do bezerro cobra
        lucro_melhor = valor_compra + porcentagem_cliente(fee_criador) * calcular_lucro_peso(peso_inicial, peso_melhor_cenario, preco_final)
        lucro_pior = valor_compra + porcentagem_cliente(fee_criador) * calcular_lucro_peso(peso_inicial, peso_pior_cenario, preco_final)

        resultados_melhor_cenario.append((trimestre, peso_melhor_cenario, valor_compra, lucro_melhor))
        resultados_pior_cenario.append((trimestre,peso_pior_cenario, valor_compra, lucro_pior))
    
    return resultados_melhor_cenario, resultados_pior_cenario

# Função que recebe a taxa de FEE que o CRIADOR do bezerro cobra e retorna o inverso para calcular o lucro do cliente
def porcentagem_cliente(taxa_fee):
    return (1 - (taxa_fee/100)) 

def calcular_lucro_peso (peso_inicial, peso_final, preco_venda):
    return preco_venda * (peso_final- peso_inicial)

# Função de cálculo do rendimento do CDI
def calcular_rendimento_cdi (valor_investido, cdi_taxas):
    # Cálculo de rendimento acumulado baseado nas taxas CDI
    rendimento_acumulado = valor_investido
    for taxa in cdi_taxas:
        rendimento_acumulado *= (1+ taxa/100)

    return rendimento_acumulado

def obter_taxas_cdi():
    url = f'https://api.bcb.gov.br/dados/serie/bcdata.sgs.12/dados?formato=json'
    response= requests.get(url)

    if response.status_code == 200:
        dados = response.json()
        taxas = [float(item['valor']) for item in dados]
        return taxas
    
    else:
        st.error('Não foi possível obter os dados do CDI.')
        return []
    
# Função para prever as taxas CDI com base no histórico
def prever_taxas_cdi (taxas, tempo_meses):
    indices = np.arange(len(taxas_cdi)).reshape(-1,1)
    modelo = LinearRegression()
    modelo.fit(indices, taxas)

    novos_indices = np.arange(len(taxas), len(taxas) +tempo_meses).reshape(-1,1)
    previsoes = modelo.predict(novos_indices)

    return previsoes

def calcular_peso_trimestral(peso_inicial, meses, otimista=True):
    ganho_mensal = 10 if otimista else 5
    peso_estimado = peso_inicial + ganho_mensal * meses
    peso_maximo = 300 if otimista else 250
    return min(peso_estimado, peso_maximo)


# Configuração dos títulos
title = "Simulação de Investimento em Bezerros"
st.title(title)

# Entrada de dados pelo usuário
st.header("Dados do investimento e previsão")
preco_kg = st.number_input("Preço por kg na compra (R$):", min_value= 0.0, value= 17.0, step=0.1)
peso_inicial = st.number_input("Peso inicial do bezerro (kg):", min_value=0.0, value=100.0, step=1.0)
data_compra = st.date_input("Data de compra do bezerro:", value = datetime.now())
preco_final = st.number_input("Preço por kg na venda (R$):", min_value=0.0, value=20.0, step=0.1)
fee_criador = st.number_input("Fee criador (%):", min_value=10.0, value=50.0, step=10.0)
tempo_meses = st.slider("Tempo máximo para engordar e venda (meses): ", min_value=1, max_value=18, value=18, step=1)


if st.button("Calcular rendimento CDI e Evolução do Bezerro"):
    
    # Obter taxas CDI históricas
    taxas_cdi = obter_taxas_cdi()
    if taxas_cdi:        

        # Prever as taxas de CDI futuras com o modelo
        previsao = prever_taxas_cdi(taxas_cdi, tempo_meses)

        # Exibindo resultados do melhor e pior cenário para o bezerro
        resultados_melhor_cenario, resultados_pior_cenario = calcular_retorno_completo(preco_kg, peso_inicial, preco_final, tempo_meses, fee_criador)

        # Criar a tabela de resultados 
        tabela_cenarios = pd.DataFrame({
            "Período (Meses)": [r[0] for r in resultados_melhor_cenario],
            "Valor de Compra R$": [r[2] for r in resultados_melhor_cenario],
            "Peso (Pior Cenário)": [r[1] for r in resultados_pior_cenario],
            "Peso (Melhor Cenário)": [r[1] for r in resultados_melhor_cenario],
            "Lucro (Pior Cenário)": [r[3] for r in resultados_pior_cenario],
            "Lucro (Melhor Cenário)": [r[3] for r in resultados_melhor_cenario],
        })

        # Exibir a tabela
        st.subheader("Evolução do Peso e Lucros")
        st.table(tabela_cenarios)
      
        # Calcular o rendimento acumulado do CDI
        valor_compra = preco_kg * peso_inicial
        rendimento_cdi = valor_compra * (1 + sum(previsao) / 100)
        
        st.markdown(f"Valor de Compra: R$ {valor_compra:.2f}")

        

        # Plotar o gráfico com os três valores no retorno
        valor_venda_melhor = resultados_melhor_cenario[-1][3]
        valor_venda_pior = resultados_pior_cenario[-1][3]

        st.subheader("Comparação de Retornos")
        fig, ax= plt.subplots()
        categorias = ['CDI Previsto', 'Venda (Pior Cenário)', 'Venda (Melhor Cenário)']
        valores = [rendimento_cdi, valor_venda_pior, valor_venda_melhor]

        ax.bar(categorias, valores, color=['blue', 'red', 'green'])
        ax.set_ylabel("Valores (R$)")
        ax.set_title("Comparação de Retornos")

        for i, v in enumerate(valores):
            ax.text(i, v+ 50, f"R$ {v:.2f}", ha="center", va="bottom")

        st.pyplot(fig)

    else:
        st.error("Não foi possível calcular o rendimento no CDI devido à ausendia de dados.")
    