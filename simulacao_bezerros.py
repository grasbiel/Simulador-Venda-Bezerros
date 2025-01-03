import streamlit as st
import requests
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
import matplotlib.pyplot as plt
from statsmodels.tsa.statespace.sarimax import SARIMAX
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout


# Função para calcular o custo de compra, receita das vendas, lucro e retorno percentual
def calcular_retorno_completo (preco_kg, peso_inicial, preco_final, tempo_meses, fee_criador):
    
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
def prever_taxas_cdi_SARIMAX (taxas, tempo_meses):
    # Criar o modelo SARIMA
    modelo = SARIMAX(taxas, order=(1,1,1), seasonal_order=(1,0,1,12))
    resultado = modelo.fit(disp=False)


    # Fazer previsões
    previsoes = resultado.get_forecast(steps=tempo_meses)
    taxas_previstas = previsoes.predicted_mean
    return taxas_previstas.tolist()


def preparar_dados(taxas, look_back=12):
    # Normalizar dados
    scaler = MinMaxScaler(feature_range=(0,1))
    taxas_normalizadas = scaler.fit_transform(np.array(taxas).reshape(-1,1))

    # Criar as sequências de entrada (X) e saída (Y)
    X, y= [], []

    for i in range(len(taxas_normalizadas) - look_back):
        X.append(taxas_normalizadas[i: i + look_back, 0])
        y.append(taxas_normalizadas[i + look_back, 0])
        
    return np.array(X), np.array(y), scaler
        
def criar_modelo_lstm(look_back):
    model= Sequential([
        LSTM(50, return_sequences= True, input_shape=(look_back,1)),
        Dropout(0.2),
        LSTM(50, return_sequences= False),
        Dropout(0.2),
        Dense(1) # Saída única para prever a próxima taxa
    ])

    model.compile(optimizer='adam', loss='mean_squared_error')
    return model

# Preparar os dados

look_back = 12
X,y = 

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
        previsao = prever_taxas_cdi_SARIMAX(taxas_cdi, tempo_meses)

        # Exibindo resultados do melhor e pior cenário para o bezerro
        resultados_melhor_cenario, resultados_pior_cenario = calcular_retorno_completo(preco_kg, peso_inicial, preco_final, tempo_meses, fee_criador)

        # Calcular o rendimento acumulado do CDI
        valor_compra = preco_kg * peso_inicial
        rendimento_cdi = valor_compra * (1 + sum(previsao) / 100)
        rendimento_cdi_trimestral = [calcular_rendimento_cdi(valor_compra, previsao[:i]) for i in range(1, len(resultados_melhor_cenario) + 1)]

        # Criar a tabela de resultados 
        tabela_cenarios = pd.DataFrame({
            "Período (Meses)": [r[0] for r in resultados_melhor_cenario],
            "Peso (Pior Cenário)": [r[1] for r in resultados_pior_cenario],
            "Peso (Melhor Cenário)": [r[1] for r in resultados_melhor_cenario],
            "Lucro (Pior Cenário)": [r[3] for r in resultados_pior_cenario],
            "Lucro (Melhor Cenário)": [r[3] for r in resultados_melhor_cenario],
            "Rendimento CDI Previsto (R$)": rendimento_cdi_trimestral
        })

        # Exibir a tabela
        st.subheader("Evolução do Peso e Lucros")
        st.table(tabela_cenarios)
      
        
        
        st.markdown(f"Valor de Compra: R$ {valor_compra:.2f}")

        # Calcular a evolução mensal (ou trimestral)
        datas = [data_compra + timedelta(days=30*i) for i in range(tempo_meses + 1)]
        cdi_acumulado = [calcular_rendimento_cdi(valor_compra, previsao[:i]) for i in range(1, len(datas) + 1)]
        melhor_cenario = [resultado[3] for resultado in resultados_melhor_cenario]
        pior_cenario = [resultado[3] for resultado in resultados_pior_cenario]

        # Ajustar datas para trimestrais
        datas_trimestrais = datas[::3]
        cdi_trimestral = cdi_acumulado[::3]
        melhor_cenario_trimestral = melhor_cenario
        pior_cenario_trimestral = pior_cenario

        # Plotar o gráfico histórico
        st.subheader("Evolução Mensal dos Retornos")
        fig, ax = plt.subplots(figsize=(10,6))
        ax.plot(datas_trimestrais, cdi_trimestral, label="CDI Previsto", marker='o', color='blue')
        ax.plot(datas_trimestrais, melhor_cenario_trimestral, label="Melhor Cenário", marker='o', color='green')
        ax.plot(datas_trimestrais, pior_cenario_trimestral, label="Pior Cenário", marker='o', color='red')

        ax.set_xlabel("Data")
        ax.set_ylabel("Valor (R$)")
        ax.set_title("Evolução Trimestral dos Retornos")
        ax.legend()
        ax.grid()


        st.pyplot(fig)
    else:
        st.error("Não foi possível calcular o rendimento no CDI devido à ausendia de dados.")
    