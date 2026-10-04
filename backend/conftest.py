import os

# Testes nunca rodam como produção, mesmo que o .env local diga o contrário
# (load_dotenv não sobrescreve variáveis já definidas).
os.environ["ENVIRONMENT"] = "test"
