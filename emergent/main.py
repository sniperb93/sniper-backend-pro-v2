from flask import Flask, jsonify
import os
from dotenv import load_dotenv

# Charge automatiquement les variables depuis .env (si présent)
load_dotenv()

app = Flask(__name__)
app.config['ENV'] = os.getenv('FLASK_ENV', 'production')

# Enregistre blueprints
try:
    from emergent.agents.builder.routes import builder_bp
    app.register_blueprint(builder_bp, url_prefix="/builder")
except Exception:
    pass

try:
    from emergent.stripe.stripe_routes import stripe_bp
    app.register_blueprint(stripe_bp, url_prefix="/stripe")
except Exception:
    pass

try:
    from emergent.trader.control import control_bp
    app.register_blueprint(control_bp, url_prefix="/trader")
except Exception:
    pass

try:
    from emergent.executor.routes import agent_exec_bp
    app.register_blueprint(agent_exec_bp, url_prefix="/executor")
except Exception:
    pass

@app.route("/")
def index():
    return jsonify({"status":"ok","service":"emergent"}), 200

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)