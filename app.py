from flask import Flask, render_template, request, redirect
import sqlite3
import pandas as pd
import random
from sklearn.metrics.pairwise import cosine_similarity
import os
import json

app = Flask(__name__)

# -----------------------------
# Conexión a la base
# -----------------------------
# -----------------------------
# Conexión a la base
# -----------------------------
def get_db_connection():
    # Carpeta base de este script
    base_dir = os.path.dirname(os.path.abspath(__file__))

    # Rutas posibles
    db_path_local = os.path.join(base_dir, 'datos', 'Datos.db')            # local
    db_path_remote = '/home/Toxic21/sr/datos/Datos.db'                     # PythonAnywhere

    # Elegir ruta según existencia
    if os.path.exists(db_path_remote):
        db_path = db_path_remote
    elif os.path.exists(db_path_local):
        db_path = db_path_local
    else:
        raise FileNotFoundError("No se encontró la base de datos ni local ni remota")

    # Conexión segura para Flask
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn
# -----------------------------
# Sistema de recomendación
# -----------------------------
def get_recommendations(user_id):
    conn = get_db_connection()
    df = pd.read_sql_query("SELECT * FROM Datos", conn)
    conn.close()

    INTERACCIONES_LIMIT = 10 # Cantidad de interacciones mínimas para considerar que el usuario es comparable con los demas.
    user_counts = df['user_id'].value_counts()
    df = df[df['user_id'].isin(user_counts[user_counts >= INTERACCIONES_LIMIT].index)]
    business_counts = df['business_id'].value_counts()
    df_filtrado = df[df['user_id'].isin(user_counts[user_counts >= INTERACCIONES_LIMIT].index)]
    df_filtrado = df_filtrado[df_filtrado['business_id'].isin(business_counts[business_counts >= 20].index)]

    # Verificación
    if not {'user_id', 'business_id', 'stars'}.issubset(df.columns):
        raise ValueError("Se necesitan columnas: user_id, business_id, stars")

    # Matriz usuario-negocio
    user_business_matrix = df_filtrado.pivot_table(index="user_id", columns="business_id", values="stars").fillna(0)

    # Usuario nuevo → 5 negocios al azar
    if user_id not in user_business_matrix.index:
        return random.sample(list(df['business_id'].unique()), 5)

    # Calcular similitud entre usuarios
    similarity = cosine_similarity(user_business_matrix)
    similarity_df = pd.DataFrame(similarity, index=user_business_matrix.index, columns=user_business_matrix.index)

    # Buscar usuarios más parecidos
    similar_users = similarity_df[user_id].sort_values(ascending=False).iloc[1:6].index

    # Restaurantes valorados por usuarios similares
    similar_ratings = df[df['user_id'].isin(similar_users)]

    # Promedios de esos restaurantes
    mean_ratings = similar_ratings.groupby('business_id')['stars'].mean().sort_values(ascending=False)

    # Excluir restaurantes ya valorados por el usuario
    rated_by_user = df[df['user_id'] == user_id]['business_id'].unique()
    candidates = mean_ratings[~mean_ratings.index.isin(rated_by_user)]

    # Si quedan pocos, completar al azar
    if len(candidates) < 5:
        restantes = list(set(df['business_id'].unique()) - set(rated_by_user))
        adicionales = random.sample(restantes, min(5 - len(candidates), len(restantes)))
        recommended_businesses = list(candidates.index[:5]) + adicionales
    else:
        recommended_businesses = list(candidates.index[:5])

    return recommended_businesses

# -----------------------------
# Rutas Flask
# -----------------------------
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user_id = request.form['user_id']
        conn = get_db_connection()
        conn.execute("INSERT OR IGNORE INTO usuarios (user_id) VALUES (?);", (user_id,))
        conn.commit()
        conn.close()
        return redirect(f'/recomendaciones/{user_id}')
    return render_template('login.html')

@app.route('/recomendaciones/<user_id>', methods=['GET', 'POST'])
def recomendaciones(user_id):
    conn = get_db_connection()

    # Guardar valoraciones nuevas
    if request.method == 'POST':
        ratings_json = request.form.get('ratings')
        if ratings_json:
            try:
                ratings = json.loads(ratings_json)
            except json.JSONDecodeError:
                ratings = {}
            for business_name, stars in ratings.items():
                row = conn.execute(
                    "SELECT DISTINCT business_id FROM Datos WHERE name = ?",
                    (business_name,)
                ).fetchone()
                if row:
                    business_id = row['business_id']
                    conn.execute(
                        "INSERT OR REPLACE INTO Datos (user_id, business_id, stars) VALUES (?, ?, ?)",
                        (user_id, business_id, int(stars))
                    )
            conn.commit()

    # Obtener nuevas recomendaciones
    recomendaciones_ids = get_recommendations(user_id)

    # Nombres de los negocios
    df = pd.read_sql_query("SELECT DISTINCT business_id, name FROM Datos", conn)
    conn.close()
    recomendados = [
        df.loc[df['business_id'] == bid, 'name'].values[0]
        for bid in recomendaciones_ids if bid in df['business_id'].values
    ]

    return render_template('recomendaciones.html', user_id=user_id, restaurantes=recomendados)

# -----------------------------
# Ejecutar servidor
# -----------------------------
if __name__ == '__main__':
    app.run(debug=True)
