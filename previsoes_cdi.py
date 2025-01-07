import numpy as np
import tensorflow as tf
from tensorflow import keras
from keras import layers
from sklearn.preprocessing import MinMaxScaler
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import mean_squared_error, mean_absolute_error

def preparar_dados (taxas, look_back=12):
    scaler = MinMaxScaler(feature_range=(0,1))
    taxas_normalizadas = scaler.fit_transform(np.array(taxas).reshape(-1,1))
    X, y = [], []

    for i in range(len(taxas_normalizadas) - look_back):
        X.append(taxas_normalizadas[i:i + look_back, 0])
        y.append(taxas_normalizadas[i + look_back, 0])

    return np.array(X), np.array(y), scaler


def criar_modelo_lstm(look_back):
    model = keras.Sequential([
        layers.LSTM(64, return_sequences=True, input_shape=(look_back, 1)),
        layers.Dropout(0.3),
        layers.LSTM(64, return_sequences=False),
        layers.Dropout(0.3),
        layers.Dense(1)
    ])
    model.compile(optimizer='adam', loss='mean_squared_error')
    return model
def avaliar_modelo(real, previsto):
    mse = mean_squared_error(real, previsto)
    mae = mean_absolute_error(real, previsto)
    rmse = np.srqt(mse)

    print(f'MSE: {mse: .4f}, MAE: {mae: .4f}, RMSE: {rmse: .4f}')

def treinar_modelo (taxas):
    look_back= 12
    X, y, scaler = preparar_dados(taxas, look_back)
    X = X.reshape(X.shape[0], X.shape[1], 1)
    modelo = criar_modelo_lstm(look_back)
    modelo.fit(X,y, epochs=10, batch_size=16, validation_split=0.2, verbose= 1)
    return modelo, scaler, look_back

def treinar_modelo_com_cv(taxas, look_back):
    X, y, scaler =  preparar_dados(taxas, look_back)
    X = X.reshape(X.shape[0], X.shape[1], 1)

    # Validação Cruzada
    tscv = TimeSeriesSplit(n_splits= 5)
    for train_index, test_index in tscv.split(X):
        X_train, X_test = X[train_index], X[test_index]
        y_train, y_test = y[train_index], y[test_index]

        modelo = criar_modelo_lstm(look_back)
        modelo.fit(X_train, y_train, epochs=20, batch_size=16, validation_data=(X_test, y_test), verbose=1)

        # Avaliar o modelo
        previsao = modelo.predict(X_test)
        avaliar_modelo(y_test, previsao)

    return modelo, scaler, look_back


def prever_taxas_cdi_lstm (modelo, taxas, scaler, look_back, tempo_meses):
    input_seq = np.array(taxas[-look_back:]).reshape(1, look_back, 1)
    input_seq = scaler.transform(input_seq.reshape(-1,1)).reshape(1, look_back, 1)
    previsoes=[]
    for _ in range(tempo_meses):
        pred = modelo.predict(input_seq)
        pred = np.array(pred).reshape(1,1,1)
        previsoes.append(pred[0][0]) # Armazena a previsão
        input_seq = np.concatenate([input_seq[:, 1:, :], pred], axis=1)
    
    previsoes = scaler.inverse_transform(np.array(previsoes).reshape(-1, 1))

    return previsoes.flatten()

