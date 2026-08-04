"""
ARQUIVO HISTÓRICO — não faz parte do fluxo atual.

O login é passwordless (magic link). Para cadastrar operadores use a UI
Admin (/admin/usuarios) ou POST /auth/users. Não edite hashed_password
manualmente para “senha de login” — essa senha não é usada.
"""
from passlib.context import CryptContext
import sys

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    """Gera hash seguro bcrypt para a senha."""
    return pwd_context.hash(password)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        password = sys.argv[1]
    else:
        password = input("Digite a senha para gerar o hash: ")
    
    print("\nO seu hash de segurança bcrypt é:")
    print("-----------------------------------")
    print(hash_password(password))
    print("-----------------------------------")
    print("(Legado) Copie este valor para 'hashed_password' em users.json —")
    print("não habilita login por senha; o produto usa magic link.")
