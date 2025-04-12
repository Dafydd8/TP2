from flask import Flask, request, redirect

app = Flask(__name__)

@app.route('/')
def login():
    return 'Inicio de sesión completado. Puedes cerrar esta ventana.'

@app.route('/callback')
def callback():
    code = request.args.get('code')
    return f"Código recibido: {code}"

if __name__ == '__main__':
    app.run(port=1234)