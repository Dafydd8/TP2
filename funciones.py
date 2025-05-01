import pandas as pd
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from sklearn.preprocessing import PolynomialFeatures

def sort_by_ts(df):
    '''
    Ordena el DataFrame 'df' por la columna 'ts' y resetea el índice.
    '''
    df = df.sort_values('ts').reset_index(drop=True)
    return df

def separate_ts(df):
    '''
    Separa la columna 'ts' en varias columnas: 'hour', 'day_of_week', 'month', 'year'.
    '''
    df['ts'] = pd.to_datetime(df['ts'])

    # Extraer la hora
    df['hour'] = df['ts'].dt.hour

    # Extraer el día de la semana (0 es lunes, 6 es domingo)
    df['day_of_week'] = df['ts'].dt.dayofweek

    # Extraer el mes
    df['month'] = df['ts'].dt.month

    # Extraer el año
    df['year'] = df['ts'].dt.year - 2000
    return

def get_is_iphone(df):
    '''
    Crea una columna 'is_iphone' que indica si la plataforma es iOS o no.
    '''
    # del dispositivo, solo queremos saber si se reprodujo en celular (iphone) o no
    df['is_iphone'] = df['platform'].apply(lambda x: 1 if ('ios' in x or 'iOS' in x) else 0)

    # dropeamos platform
    df = df.drop(columns=['platform'])
    return

def encode_reasons_muchas(df):
    '''
    Codifica la columna 'reason_start' con  One Hot Encoding.
    '''
    expected_columns = ['reason_appload', 'reason_backbtn', 'reason_clickrow',
    'reason_fwdbtn', 'reason_playbtn', 'reason_remote', 'reason_trackdone',
    'reason_trackerror', 'reason_unknown']
    # Aplicar One-Hot Encoding a razon de reproduccion
    df_encoded = pd.get_dummies(df['reason_start'], prefix='reason', dummy_na=False)
    for col in expected_columns:
        if col not in df_encoded.columns:
            df_encoded[col] = 0

    # 
    df_encoded = df_encoded[expected_columns]

    # Concatenar el dfFrame original con el nuevo dfFrame de variables codificadas
    df = pd.concat([df, df_encoded], axis=1)

    # Dropear la columna original
    df = df.drop(columns=['reason_start'])
    return df

def calculate_is_early_finish(df):
    '''
    Requiere: df esta ordenado por 'ts'.
    Calcula si la canción se terminó antes de lo esperado.
    Añade una columna 'is_early_finish' al DataFrame 'df'.
    '''
    # Inicializamos la columna en 0
    df['is_early_finish'] = 0
    for i in range(1, len(df)):
        ts_actual = df.at[i, 'ts']
        ts_anterior = df.at[i-1, 'ts']
        try:
            reproducciones_seguidas = df.at[i, 'reason_start'] in ['fwdbtn', 'trackdone', 'backbtn', 'trackerror', 'unknown']
            d = pd.Timedelta(milliseconds=df.at[i, 'duration_ms'])
            if reproducciones_seguidas:
                if ts_actual-d < ts_anterior:
                    df.at[i, 'is_early_finish'] = 1
        except:
            #print('No se encontró duration_ms para la canción')
            continue
    return df

def calculate_racha_early_finish(df):
    df['racha_early_finish'] = 0
    for i in range(1, len(df)):
        if df.at[i, 'is_early_finish'] == 1:
            df.at[i, 'racha_early_finish'] = df.at[i-1, 'racha_early_finish'] + 1
    return df

def racha_razon_hasta_ahora(df, razon:str):
    '''
    Requiere: df esta ordenado por 'ts'.
    Añade una columna a df que indica, para la observación actual, cuantas observaciones previas seguidas tenian razón como reason_start.
    '''
    # Inicializamos la columna en 0
    new_col = f'{razon}_seguidos'
    df[new_col] = 0
    
    for i in range(1, len(df)):
        if df.at[i, f'reason_{razon}'] == 1:
            df.at[i, new_col] = df.at[i-1, new_col] + 1
    return df

def es_racha(df, razon):
    '''
    Requiere: df esta ordenado por 'ts'.
    Añade una columna a df que indica 1 si la racha de razón de reproducción es > 1, 0 en caso contrario.
    '''
    # Inicializamos la columna en 0
    new_col = f'{razon}_spree'
    df[new_col] = 0
    
    # Iteramos desde la segunda fila
    for i in range(0, len(df)):
        if df.at[i, f'{razon}_seguidos'] > 1:
            df.at[i, new_col] = 1
    return df

def calculate_prop_fwdbtn_periodo(df, periodo:int):
    '''
    Requiere: df esta ordenado por 'ts'.
    Calcula la proporción de fwdbtn en los últimos 'periodo' minutos y lo añade al DataFrame 'df'.
    '''
    # Inicializamos la columna en 0
    new_col = f'fwdbtn_prop_{periodo}'
    df[new_col] = 0
    
    # Iteramos desde la segunda fila
    for i in range(1, len(df)):
        ts_actual = df.at[i, 'ts']
        delta = pd.Timedelta(minutes=periodo)
        obs = df[(df['ts'] >= ts_actual - delta) & (df['ts'] <= ts_actual)]
        suma = 0
        for j in range(len(obs)):
            if obs.iloc[j]['reason_fwdbtn'] == 1:
                suma += 1
        df.at[i, new_col] = suma / len(obs) if len(obs) > 0 else 0
    return df

def calculate_prop_reason_periodo_rolling(df, periodo:int, reason):
    new_col = f'{reason}_prop_{periodo}'
    df = df.set_index('ts').sort_index()
    
    # rolling count and rolling sum sobre los últimos `periodo` minutos
    ventana = f'{periodo}T'   # 'T' indica minutos
    suma = df[f'reason_{reason}'].rolling(ventana).sum()
    conteo = df[f'reason_{reason}'].rolling(ventana).count()
    
    df[new_col] = (suma / conteo).fillna(0)
    
    # volver a poner ts como columna
    df = df.reset_index()
    return df


def get_spotify_auth():
    '''
    Configura la autenticación de Spotify utilizando Spotipy y devuelve el objeto de autenticación.
    Si no se puede obtener el token, imprime un mensaje de error.
    '''
    # Configura el objeto SpotifyOAuth
    auth_manager = SpotifyOAuth(
        client_id="bd28f888d5594351a74597b8c4750b07",
        client_secret="2ad3d9ea7c00425792697d028c5afbd5",
        redirect_uri="http://127.0.0.1:1234/",
        scope="user-top-read",
        open_browser=False
    )
    if auth_manager != None:
        return auth_manager
    else:
        # Si no se puede obtener el token, abre el navegador para la autenticación
        print("Error al obtener el token")
    return 

def chunk_list(lst, size):
    """Divide la lista 'lst' en sublistas de tamaño 'size'."""
    return [lst[i:i + size] for i in range(0, len(lst), size)]

def get_songs_durations(df):
    '''
    Obtiene la duración de las canciones a partir de los URIs de Spotify en el DataFrame 'df'.
    Devuelve un diccionario que mapea los URIs a sus duraciones en milisegundos.
    '''
    manager = get_spotify_auth()
    sp = spotipy.Spotify(auth_manager=manager)
    # Obtener la duración de las canciones
    # Obtener los URIs únicos y válidos
    tracks = df['spotify_track_uri'].dropna().unique()  # Elimina NaN directamente
    tracks = [uri for uri in tracks if isinstance(uri, str)]  # Filtra que sean strings

    # Dividir en chunks de hasta 50 elementos
    chunks = chunk_list(tracks, 50)
    uri_to_duration = {}
    for i, chunk in enumerate(chunks):
        print(i)
        try:
            tracks_info = sp.tracks(chunk)  # Consulta a la API
            for track in tracks_info.get('tracks', []):
                if track:
                    uri = track.get('uri')
                    duration = track.get('duration_ms')
                    uri_to_duration[uri] = duration
                else:
                    print("⚠️  Track no encontrado o no disponible.")
        except Exception as e:
            print(f"❌ Error al procesar el chunk {i + 1}: {e}")
    return uri_to_duration


def calculate_durations(df, diccionario):
    '''
    Añade una columna 'duration_ms' al DataFrame 'df' con la duración de las canciones en milisegundos.
    '''
    def get_duration(uri):
        return diccionario.get(uri, None)

    df['duration_ms'] = df['spotify_track_uri'].apply(get_duration)
    return df

def get_proporciones(df):
    '''
    Agrega a df las columnas con las proporciones de cada valor único en cada columna de columnas.
    '''
    df['track_prop'] = df.groupby('master_metadata_track_name')['master_metadata_track_name'].transform('count')/len(df)
    df['artist_prop'] = df.groupby('master_metadata_album_artist_name')['master_metadata_album_artist_name'].transform('count')/len(df)
    df['album_prop'] = df.groupby('master_metadata_album_album_name')['master_metadata_album_album_name'].transform('count')/len(df)

    return df

def comb_polinom(df, cols):
    '''
    Crea combinaciones polinómicas de las columnas especificadas en 'cols'.
    Se eliminan las columnas originales y se añaden las nuevas combinaciones al DataFrame 'df'.
    '''
    # Crear combinaciones polinómicas de las columnas especificadas
    poly = PolynomialFeatures(degree=2, interaction_only=True, include_bias=False)
    poly_features = poly.fit_transform(df[cols])
    
    # Crear un DataFrame con los nombres de las nuevas columnas
    feature_names = poly.get_feature_names_out(cols)
    poly_df = pd.DataFrame(poly_features, columns=feature_names, index=df.index)
    poly_df = poly_df.drop(columns=cols)  # Eliminar las columnas originales
    
    # Concatenar el DataFrame original con el nuevo DataFrame de características polinómicas
    df = pd.concat([df.reset_index(drop=True), poly_df.reset_index(drop=True)], axis=1)
    return df

def procesar_df(df, diccionario):
    '''
    Procesa el DataFrame 'df' aplicando las funciones de separación de tiempo, codificación de razones,
    cálculo de rachas, obtención de duraciones y combinaciones polinómicas.
    DF QUEDA ORDEADO POR 'ts'!
    '''
    df = df.drop(columns=['username', 'conn_country', 'user_agent_decrypted'])
    df = sort_by_ts(df)
    separate_ts(df)
    get_is_iphone(df)
    df = calculate_durations(df, diccionario)
    df = calculate_is_early_finish(df)
    df = calculate_racha_early_finish(df)
    df = encode_reasons_muchas(df)
    #df = racha_razon_hasta_ahora(df, 'fwdbtn')
    #df = racha_razon_hasta_ahora(df, 'trackdone')
    #df = es_racha(df, 'fwdbtn')
    #df = es_racha(df, 'trackdone')
    # for reason in ['fwdbtn', 'trackdone', 'clickrow      ', ]:
    #     df = racha_razon_hasta_ahora(df, reason)
    #     df = es_racha(df, reason)
    # df = calculate_prop_reason_periodo_rolling(df, 10, 'fwdbtn')
    # df = calculate_prop_reason_periodo_rolling(df, 10, 'trackdone')
    # df = calculate_prop_reason_periodo_rolling(df, 10, 'playbtn')
    df = get_proporciones(df)
    df = comb_polinom(df, ['hour', 'day_of_week'])
    return df
    